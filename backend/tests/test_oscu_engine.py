"""OSCU simulator: control codes, QR, persistence, SMS, and tamper detection."""

import base64
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.etims import CreateInvoiceRequest
from app.schemas.tax import TaxLineInput
from app.models.invoice import Invoice
from app.services.oscu_engine import (
    format_control_code,
    issue_invoice,
    sign_payload,
    signature_valid,
    verify_control_code,
)
from app.services.sms_dispatcher import normalize_msisdn
from app.services.tax_engine import TaxValidationError


def _sale(**overrides) -> CreateInvoiceRequest:
    payload = {
        "trader_pin": "A012345678W",
        "trader_name": "JibuTax Demo Trader",
        "trader_phone": "0712345678",
        "buyer_pin": "P051234567M",
        "buyer_name": "Safari Builders",
        "items": [
            TaxLineInput(
                description="bags of cement",
                quantity=Decimal("100"),
                unit_price=Decimal("2000"),
            )
        ],
        "send_sms": True,
    }
    payload.update(overrides)
    return CreateInvoiceRequest(**payload)


def test_control_code_is_grouped_hex():
    assert format_control_code("abcdef0123456789ffff") == "ABCD-EF01-2345-6789"


def test_same_payload_same_hmac():
    first = sign_payload('{"grand_total":"232000.00"}', "test-oscu-secret")
    second = sign_payload('{"grand_total":"232000.00"}', "test-oscu-secret")
    assert first == second
    assert len(first) == 64


def test_amount_change_changes_hmac():
    secret = "test-oscu-secret"
    left = sign_payload('{"grand_total":"232000.00"}', secret)
    right = sign_payload('{"grand_total":"232001.00"}', secret)
    assert left != right


def test_issue_cement_sale_signs_and_texts(db: Session, settings: Settings):
    invoice = issue_invoice(db, _sale(), settings)
    assert invoice.invoice_number == "INV-2026-00001"
    assert invoice.cu_invoice_number == "KRACU0000000001"
    assert invoice.grand_total == Decimal("232000.00")
    assert invoice.total_vat_amount == Decimal("32000.00")
    assert invoice.buyer_pin == "P051234567M"
    assert invoice.oscu_control_code.count("-") == 3
    assert invoice.signature_valid is True
    assert invoice.sms_status == "mocked"
    assert invoice.sms_destination == "+254712345678"
    assert "INV-2026-00001" in invoice.sms_body
    assert invoice.whatsapp_status == "mocked"
    assert invoice.whatsapp_destination == "+254712345678"
    assert "INV-2026-00001" in invoice.whatsapp_body
    png = base64.b64decode(invoice.qr_code_base64)
    assert png.startswith(b"\x89PNG")


def test_walk_in_customer_without_buyer_pin(db: Session, settings: Settings):
    invoice = issue_invoice(db, _sale(buyer_pin=None, buyer_name=None), settings)
    assert invoice.buyer_pin is None
    assert invoice.buyer_name == "WALK-IN CUSTOMER"


def test_invalid_buyer_pin_is_rejected(db: Session, settings: Settings):
    with pytest.raises(TaxValidationError) as exc:
        issue_invoice(db, _sale(buyer_pin="12345"), settings)
    assert exc.value.code == "INVALID_PIN"


def test_buyer_cannot_be_seller(db: Session, settings: Settings):
    with pytest.raises(TaxValidationError) as exc:
        issue_invoice(db, _sale(buyer_pin="A012345678W"), settings)
    assert exc.value.code == "SAME_PARTY"


def test_invoice_numbers_increment(db: Session, settings: Settings):
    first = issue_invoice(db, _sale(), settings)
    second = issue_invoice(db, _sale(buyer_name="Second Buyer"), settings)
    assert first.invoice_number == "INV-2026-00001"
    assert second.invoice_number == "INV-2026-00002"


def test_verify_returns_valid_invoice(db: Session, settings: Settings):
    issued = issue_invoice(db, _sale(), settings)
    invoice, valid, message = verify_control_code(db, issued.oscu_control_code, settings)
    assert valid is True
    assert invoice is not None
    assert "valid" in message.lower()


def test_unknown_control_code(db: Session, settings: Settings):
    invoice, valid, message = verify_control_code(db, "DEAD-BEEF-0000-0000", settings)
    assert invoice is None
    assert valid is False
    assert "No eTIMS" in message


def test_tampered_total_fails_signature(db: Session, settings: Settings):
    issue_invoice(db, _sale(), settings)
    row = db.query(Invoice).one()
    row.grand_total = Decimal("1.00")
    db.commit()
    db.refresh(row)
    assert signature_valid(row, settings.oscu_signing_secret) is False


def test_invalid_phone_still_files_invoice(db: Session, settings: Settings):
    invoice = issue_invoice(db, _sale(trader_phone="not-a-phone"), settings)
    assert invoice.invoice_number.startswith("INV-")
    assert invoice.sms_status == "skipped_invalid_phone"
    assert invoice.whatsapp_status == "skipped_invalid_phone"


def test_normalize_kenyan_msisdn():
    assert normalize_msisdn("0712345678") == "+254712345678"
    assert normalize_msisdn("+254712345678") == "+254712345678"
    assert normalize_msisdn("254712345678") == "+254712345678"
    assert normalize_msisdn("020123456") is None
