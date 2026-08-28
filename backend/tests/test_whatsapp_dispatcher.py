"""WhatsApp QR dispatch: mock, Meta Cloud API, Twilio, and webhook verification."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import Settings
from app.api.v1.whatsapp import verify_whatsapp_webhook
from app.schemas.etims import CreateInvoiceRequest
from app.schemas.tax import TaxLineInput
from app.services.oscu_engine import issue_invoice, qr_png_bytes
from app.services.whatsapp_dispatcher import dispatch_qr_receipt, format_receipt_whatsapp
from decimal import Decimal
from sqlalchemy.orm import Session


PNG = b"\x89PNG\r\n\x1a\n" + b"fake-qr"


def _settings(**overrides) -> Settings:
    values = dict(
        whatsapp_provider="mock",
        public_base_url="http://testserver",
        oscu_signing_secret="test-oscu-secret",
    )
    values.update(overrides)
    return Settings(**values)


def test_caption_includes_control_and_qr_hint():
    body = format_receipt_whatsapp(
        invoice_number="INV-2026-00001",
        cu_invoice_number="KRACU0000000001",
        buyer_name="Safari Builders",
        grand_total=Decimal("232000.00"),
        vat_amount=Decimal("32000.00"),
        control_code="ABCD-EF01-2345-6789",
        verify_url="http://testserver/api/v1/invoices/verify/ABCD-EF01-2345-6789",
    )
    assert "*JibuTax eTIMS receipt*" in body
    assert "INV-2026-00001" in body
    assert "ABCD-EF01-2345-6789" in body
    assert "Scan the QR" in body


def test_mock_dispatch_normalizes_kenyan_msisdn():
    result = dispatch_qr_receipt(
        phone="0712345678",
        caption="receipt",
        qr_png=PNG,
        invoice_number="INV-2026-00001",
        settings=_settings(),
    )
    assert result.status == "mocked"
    assert result.destination == "+254712345678"


def test_invalid_phone_is_skipped():
    result = dispatch_qr_receipt(
        phone="not-a-phone",
        caption="receipt",
        qr_png=PNG,
        invoice_number="INV-2026-00001",
        settings=_settings(),
    )
    assert result.status == "skipped_invalid_phone"
    assert result.destination is None


def test_meta_without_keys_is_not_configured():
    result = dispatch_qr_receipt(
        phone="0712345678",
        caption="receipt",
        qr_png=PNG,
        invoice_number="INV-2026-00001",
        settings=_settings(whatsapp_provider="meta"),
    )
    assert result.status == "skipped_not_configured"


def test_twilio_without_public_https_is_skipped():
    result = dispatch_qr_receipt(
        phone="0712345678",
        caption="receipt",
        qr_png=PNG,
        invoice_number="INV-2026-00001",
        settings=_settings(
            whatsapp_provider="twilio",
            twilio_account_sid="ACxxx",
            twilio_auth_token="secret",
            public_base_url="http://localhost:8000",
        ),
    )
    assert result.status == "skipped_public_url_required"


def test_meta_uploads_png_then_sends_image():
    upload = MagicMock()
    upload.raise_for_status = MagicMock()
    upload.json.return_value = {"id": "MEDIA123"}
    send = MagicMock()
    send.raise_for_status = MagicMock()
    send.json.return_value = {"messages": [{"id": "wamid.abc"}]}

    with patch("app.services.whatsapp_dispatcher.httpx.post", side_effect=[upload, send]) as posted:
        result = dispatch_qr_receipt(
            phone="+254712345678",
            caption="Scan the QR",
            qr_png=PNG,
            invoice_number="INV-2026-00001",
            settings=_settings(
                whatsapp_provider="meta",
                whatsapp_meta_token="EAAtest",
                whatsapp_meta_phone_number_id="123456789",
            ),
        )

    assert result.status == "sent"
    assert result.provider_id == "wamid.abc"
    media_call, message_call = posted.call_args_list
    assert "/123456789/media" in media_call.args[0]
    assert media_call.kwargs["files"]["file"][0] == "etims-qr.png"
    payload = message_call.kwargs["json"]
    assert payload["to"] == "254712345678"
    assert payload["image"]["id"] == "MEDIA123"
    assert payload["image"]["caption"] == "Scan the QR"


def test_twilio_sends_media_url():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"sid": "SM123"}

    with patch("app.services.whatsapp_dispatcher.httpx.post", return_value=response) as posted:
        result = dispatch_qr_receipt(
            phone="0712345678",
            caption="Scan the QR",
            qr_png=PNG,
            invoice_number="INV-2026-00001",
            settings=_settings(
                whatsapp_provider="twilio",
                twilio_account_sid="ACxxx",
                twilio_auth_token="secret",
                public_base_url="https://jibutax.example.com",
            ),
        )

    assert result.status == "sent"
    assert result.provider_id == "SM123"
    data = posted.call_args.kwargs["data"]
    assert data["To"] == "whatsapp:+254712345678"
    assert data["MediaUrl"] == "https://jibutax.example.com/api/v1/invoices/INV-2026-00001/qr.png"


def test_meta_http_error_is_failed():
    failed = MagicMock()
    failed.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    with patch("app.services.whatsapp_dispatcher.httpx.post", return_value=failed):
        result = dispatch_qr_receipt(
            phone="0712345678",
            caption="receipt",
            qr_png=PNG,
            invoice_number="INV-2026-00001",
            settings=_settings(
                whatsapp_provider="meta",
                whatsapp_meta_token="bad",
                whatsapp_meta_phone_number_id="1",
            ),
        )
    assert result.status == "failed"
    assert result.error


def test_issue_invoice_skips_whatsapp_when_disabled(db: Session, settings: Settings):
    invoice = issue_invoice(
        db,
        CreateInvoiceRequest(
            trader_pin="A012345678W",
            trader_phone="0712345678",
            items=[TaxLineInput(description="nails", quantity=Decimal("1"), unit_price=Decimal("100"))],
            send_whatsapp=False,
        ),
        settings,
    )
    assert invoice.whatsapp_status == "skipped"
    assert invoice.sms_status == "mocked"


def test_issued_invoice_stores_qr_png(db: Session, settings: Settings):
    invoice_row = issue_invoice(
        db,
        CreateInvoiceRequest(
            trader_pin="A012345678W",
            trader_phone="0712345678",
            items=[TaxLineInput(description="nails", quantity=Decimal("1"), unit_price=Decimal("100"))],
        ),
        settings,
    )
    from app.models.invoice import Invoice

    row = db.query(Invoice).one()
    png = qr_png_bytes(row)
    assert png.startswith(b"\x89PNG")
    assert invoice_row.whatsapp_status == "mocked"


@patch("app.api.v1.whatsapp.get_settings")
def test_webhook_challenge_is_echoed(mock_settings):
    mock_settings.return_value = Settings(whatsapp_verify_token="demo-token")
    response = verify_whatsapp_webhook(
        hub_mode="subscribe",
        hub_verify_token="demo-token",
        hub_challenge="challenge-42",
    )
    assert response.body == b"challenge-42"


@patch("app.api.v1.whatsapp.get_settings")
def test_webhook_rejects_bad_token(mock_settings):
    mock_settings.return_value = Settings(whatsapp_verify_token="demo-token")
    with pytest.raises(Exception) as exc:
        verify_whatsapp_webhook(
            hub_mode="subscribe",
            hub_verify_token="wrong",
            hub_challenge="challenge-42",
        )
    assert getattr(exc.value, "status_code", None) == 403
