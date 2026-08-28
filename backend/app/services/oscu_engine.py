"""eTIMS OSCU simulator: sequential CU numbers, HMAC-SHA256 control codes, QR receipts."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import qrcode
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.invoice import Invoice, InvoiceItem
from app.schemas.etims import CreateInvoiceRequest, InvoiceItemResponse, InvoiceResponse
from app.schemas.tax import TaxBreakdown, TaxLineResult
from app.services.sms_dispatcher import dispatch_receipt, format_receipt_sms
from app.services.tax_engine import TaxValidationError, calculate_invoice, money
from app.services.whatsapp_dispatcher import dispatch_qr_receipt, format_receipt_whatsapp

logger = logging.getLogger(__name__)

EAT = ZoneInfo("Africa/Nairobi")
PIN_RE = re.compile(r"^[A-Z]\d{9}[A-Z]$")


def normalize_pin(pin: str | None, *, required: bool, field: str) -> str | None:
    if pin is None or not pin.strip():
        if required:
            raise TaxValidationError("INVALID_PIN", f"{field} is required.")
        return None
    cleaned = pin.strip().upper()
    if not PIN_RE.match(cleaned):
        raise TaxValidationError(
            "INVALID_PIN",
            f"{field} '{pin}' is not a valid KRA PIN. Expected a letter, 9 digits, then a letter.",
        )
    return cleaned


def _money_str(value: Decimal) -> str:
    return f"{money(value):.2f}"


def build_canonical_payload(
    *,
    device_id: str,
    invoice_number: str,
    cu_invoice_number: str,
    issued_at: datetime,
    trader_pin: str,
    trader_name: str,
    buyer_pin: str | None,
    buyer_name: str,
    tax: TaxBreakdown,
) -> str:
    payload = {
        "buyer_name": buyer_name,
        "buyer_pin": buyer_pin or "",
        "cu_invoice_number": cu_invoice_number,
        "device_id": device_id,
        "grand_total": _money_str(tax.grand_total),
        "invoice_number": invoice_number,
        "issued_at": issued_at.isoformat(),
        "items": [
            {
                "description": line.description,
                "hs_code": line.hs_code,
                "line_total": _money_str(line.line_total),
                "quantity": str(line.quantity),
                "tax_amount": _money_str(line.tax_amount),
                "tax_class": line.tax_class.value,
                "tax_rate": str(line.tax_rate),
                "taxable_amount": _money_str(line.taxable_amount),
                "unit_price": str(line.unit_price),
            }
            for line in tax.lines
        ],
        "total_exempt_amount": _money_str(tax.total_exempt_amount),
        "total_fuel_amount": _money_str(tax.total_fuel_amount),
        "total_fuel_tax": _money_str(tax.total_fuel_tax),
        "total_standard_amount": _money_str(tax.total_standard_amount),
        "total_standard_vat": _money_str(tax.total_standard_vat),
        "total_vat_amount": _money_str(tax.total_vat_amount),
        "total_zero_rated_amount": _money_str(tax.total_zero_rated_amount),
        "trader_name": trader_name,
        "trader_pin": trader_pin,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sign_payload(canonical: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def format_control_code(payload_hash: str) -> str:
    raw = payload_hash[:16].upper()
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"


def make_qr_base64(data: str) -> str:
    import base64

    image = qrcode.make(data)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def next_invoice_numbers(db: Session, issued_at: datetime) -> tuple[str, str]:
    year = issued_at.astimezone(EAT).year
    prefix = f"INV-{year}-"
    last = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.id.desc())
        .first()
    )
    seq = 1
    if last:
        seq = int(last.invoice_number.rsplit("-", 1)[1]) + 1
    return f"{prefix}{seq:05d}", f"KRACU{seq:010d}"


def _tax_from_invoice(invoice: Invoice) -> TaxBreakdown:
    from app.schemas.tax import TaxClassification

    lines = [
        TaxLineResult(
            description=item.description,
            hs_code=item.hs_code,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_class=TaxClassification(item.tax_class),
            tax_rate=item.tax_rate,
            taxable_amount=item.taxable_amount,
            tax_amount=item.tax_amount,
            line_total=item.line_total,
            schedule="",
        )
        for item in invoice.items
    ]
    return TaxBreakdown(
        lines=lines,
        total_standard_amount=invoice.total_standard_amount,
        total_standard_vat=invoice.total_standard_vat,
        total_fuel_amount=invoice.total_fuel_amount,
        total_fuel_tax=invoice.total_fuel_tax,
        total_exempt_amount=invoice.total_exempt_amount,
        total_zero_rated_amount=invoice.total_zero_rated_amount,
        total_vat_amount=invoice.total_vat_amount,
        grand_total=invoice.grand_total,
        spoken_en="",
        spoken_sw="",
    )


def signature_valid(invoice: Invoice, secret: str) -> bool:
    expected = sign_payload(invoice.canonical_payload, secret)
    if not hmac.compare_digest(expected, invoice.oscu_payload_hash):
        return False
    if format_control_code(invoice.oscu_payload_hash) != invoice.oscu_control_code:
        return False
    sealed = json.loads(invoice.canonical_payload)
    return (
        sealed.get("invoice_number") == invoice.invoice_number
        and sealed.get("grand_total") == _money_str(invoice.grand_total)
        and sealed.get("total_vat_amount") == _money_str(invoice.total_vat_amount)
        and sealed.get("trader_pin") == invoice.trader_pin
        and sealed.get("buyer_pin") == (invoice.buyer_pin or "")
    )


def to_response(invoice: Invoice, tax: TaxBreakdown | None = None, *, valid: bool = True) -> InvoiceResponse:
    if tax is None:
        tax = _tax_from_invoice(invoice)
        tax.spoken_en = ""
        tax.spoken_sw = ""
    return InvoiceResponse(
        invoice_number=invoice.invoice_number,
        cu_invoice_number=invoice.cu_invoice_number,
        oscu_control_code=invoice.oscu_control_code,
        oscu_payload_hash=invoice.oscu_payload_hash,
        oscu_device_id=invoice.oscu_device_id,
        trader_pin=invoice.trader_pin,
        trader_name=invoice.trader_name,
        trader_phone=invoice.trader_phone,
        buyer_pin=invoice.buyer_pin,
        buyer_name=invoice.buyer_name,
        items=[InvoiceItemResponse.model_validate(line.model_dump()) for line in tax.lines],
        total_standard_amount=invoice.total_standard_amount,
        total_standard_vat=invoice.total_standard_vat,
        total_fuel_amount=invoice.total_fuel_amount,
        total_fuel_tax=invoice.total_fuel_tax,
        total_exempt_amount=invoice.total_exempt_amount,
        total_zero_rated_amount=invoice.total_zero_rated_amount,
        total_vat_amount=invoice.total_vat_amount,
        grand_total=invoice.grand_total,
        qr_code_url=invoice.qr_code_url,
        qr_code_base64=invoice.qr_code_base64,
        sms_status=invoice.sms_status,
        sms_destination=invoice.sms_destination,
        sms_body=invoice.sms_body,
        whatsapp_status=invoice.whatsapp_status or "pending",
        whatsapp_destination=invoice.whatsapp_destination,
        whatsapp_message_id=invoice.whatsapp_message_id,
        whatsapp_body=invoice.whatsapp_body,
        signature_valid=valid,
        issued_at=invoice.issued_at,
        spoken_en=tax.spoken_en,
        spoken_sw=tax.spoken_sw,
    )


def issue_invoice(
    db: Session,
    request: CreateInvoiceRequest,
    settings: Settings | None = None,
) -> InvoiceResponse:
    settings = settings or get_settings()
    trader_pin = normalize_pin(
        request.trader_pin or settings.default_trader_pin,
        required=True,
        field="Trader PIN",
    )
    buyer_pin = normalize_pin(request.buyer_pin, required=False, field="Buyer PIN")
    trader_name = (request.trader_name or settings.default_trader_name).strip()
    buyer_name = (request.buyer_name or "WALK-IN CUSTOMER").strip()

    if buyer_pin and buyer_pin == trader_pin:
        raise TaxValidationError(
            "SAME_PARTY",
            "Buyer PIN cannot be the same as the trader PIN.",
        )

    tax = calculate_invoice(request.items, claimed_grand_total=request.claimed_grand_total)
    issued_at = datetime.now(EAT)
    invoice_number, cu_invoice_number = next_invoice_numbers(db, issued_at)
    canonical = build_canonical_payload(
        device_id=settings.kra_oscu_device_id,
        invoice_number=invoice_number,
        cu_invoice_number=cu_invoice_number,
        issued_at=issued_at,
        trader_pin=trader_pin,
        trader_name=trader_name,
        buyer_pin=buyer_pin,
        buyer_name=buyer_name,
        tax=tax,
    )
    payload_hash = sign_payload(canonical, settings.oscu_signing_secret)
    control_code = format_control_code(payload_hash)
    verify_url = f"{settings.public_base_url.rstrip('/')}/api/v1/invoices/verify/{control_code}"
    qr_payload = json.dumps(
        {
            "invoice_number": invoice_number,
            "cu_invoice_number": cu_invoice_number,
            "control_code": control_code,
            "trader_pin": trader_pin,
            "grand_total": _money_str(tax.grand_total),
            "verify": verify_url,
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    invoice = Invoice(
        invoice_number=invoice_number,
        cu_invoice_number=cu_invoice_number,
        oscu_control_code=control_code,
        oscu_payload_hash=payload_hash,
        canonical_payload=canonical,
        oscu_device_id=settings.kra_oscu_device_id,
        trader_pin=trader_pin,
        trader_name=trader_name,
        trader_phone=request.trader_phone,
        buyer_pin=buyer_pin,
        buyer_name=buyer_name,
        total_standard_amount=tax.total_standard_amount,
        total_standard_vat=tax.total_standard_vat,
        total_fuel_amount=tax.total_fuel_amount,
        total_fuel_tax=tax.total_fuel_tax,
        total_exempt_amount=tax.total_exempt_amount,
        total_zero_rated_amount=tax.total_zero_rated_amount,
        total_vat_amount=tax.total_vat_amount,
        grand_total=tax.grand_total,
        qr_code_url=verify_url,
        qr_code_base64=make_qr_base64(qr_payload),
        sms_status="pending",
        sms_destination=None,
        sms_body=format_receipt_sms(
            invoice_number=invoice_number,
            buyer_name=buyer_name,
            grand_total=tax.grand_total,
            vat_amount=tax.total_vat_amount,
            control_code=control_code,
            verify_url=verify_url,
        ),
        whatsapp_status="pending",
        whatsapp_destination=None,
        whatsapp_message_id=None,
        whatsapp_body=format_receipt_whatsapp(
            invoice_number=invoice_number,
            cu_invoice_number=cu_invoice_number,
            buyer_name=buyer_name,
            grand_total=tax.grand_total,
            vat_amount=tax.total_vat_amount,
            control_code=control_code,
            verify_url=verify_url,
        ),
        issued_at=issued_at,
        items=[
            InvoiceItem(
                description=line.description,
                hs_code=line.hs_code,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_class=line.tax_class.value,
                tax_rate=line.tax_rate,
                taxable_amount=line.taxable_amount,
                tax_amount=line.tax_amount,
                line_total=line.line_total,
            )
            for line in tax.lines
        ],
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    logger.info(
        "oscu_signed invoice=%s control=%s grand=%s buyer=%s",
        invoice.invoice_number,
        invoice.oscu_control_code,
        invoice.grand_total,
        invoice.buyer_pin or "WALK-IN",
    )

    if request.send_sms:
        sms = dispatch_receipt(phone=request.trader_phone, body=invoice.sms_body, settings=settings)
        invoice.sms_status = sms.status
        invoice.sms_destination = sms.destination
    else:
        invoice.sms_status = "skipped"

    if request.send_whatsapp:
        apply_whatsapp_dispatch(invoice, phone=request.trader_phone, settings=settings)
    else:
        invoice.whatsapp_status = "skipped"

    db.commit()
    db.refresh(invoice)

    return to_response(invoice, tax, valid=True)


def qr_png_bytes(invoice: Invoice) -> bytes:
    import base64

    return base64.b64decode(invoice.qr_code_base64)


def apply_whatsapp_dispatch(
    invoice: Invoice,
    *,
    phone: str | None = None,
    settings: Settings | None = None,
) -> Invoice:
    settings = settings or get_settings()
    result = dispatch_qr_receipt(
        phone=phone or invoice.trader_phone,
        caption=invoice.whatsapp_body or invoice.sms_body or "",
        qr_png=qr_png_bytes(invoice),
        invoice_number=invoice.invoice_number,
        settings=settings,
    )
    invoice.whatsapp_status = result.status
    invoice.whatsapp_destination = result.destination
    invoice.whatsapp_message_id = result.provider_id
    return invoice


def get_invoice(db: Session, invoice_number: str) -> Invoice | None:
    return db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()


def list_invoices(db: Session, limit: int = 50) -> list[Invoice]:
    return db.query(Invoice).order_by(Invoice.id.desc()).limit(limit).all()


def verify_control_code(db: Session, control_code: str, settings: Settings | None = None) -> tuple[Invoice | None, bool, str]:
    settings = settings or get_settings()
    invoice = db.query(Invoice).filter(Invoice.oscu_control_code == control_code.upper()).first()
    if invoice is None:
        return None, False, "No eTIMS invoice found for that control code."
    valid = signature_valid(invoice, settings.oscu_signing_secret)
    if not valid:
        return invoice, False, "Control code found but the fiscal signature does not match the stored invoice."
    return invoice, True, "Official eTIMS control code is valid."
