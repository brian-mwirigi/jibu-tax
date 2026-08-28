"""WhatsApp QR receipt dispatch. Mock by default; Meta Cloud API or Twilio when keys are set."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.config import Settings, get_settings
from app.services.sms_dispatcher import money_text, normalize_msisdn

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppResult:
    status: str
    destination: str | None
    provider_id: str | None = None
    error: str | None = None


def format_receipt_whatsapp(
    *,
    invoice_number: str,
    cu_invoice_number: str,
    buyer_name: str,
    grand_total: Decimal,
    vat_amount: Decimal,
    control_code: str,
    verify_url: str,
) -> str:
    return (
        f"*JibuTax eTIMS receipt*\n"
        f"INV {invoice_number}\n"
        f"CU {cu_invoice_number}\n"
        f"Buyer: {buyer_name}\n"
        f"Total KES {money_text(grand_total)}\n"
        f"VAT KES {money_text(vat_amount)}\n"
        f"Code {control_code}\n"
        f"Scan the QR to verify.\n"
        f"{verify_url}"
    )


def _configured_provider(settings: Settings) -> str:
    return (settings.whatsapp_provider or "mock").strip().lower()


def _is_public_https(url: str) -> bool:
    lowered = url.lower()
    if not lowered.startswith("https://"):
        return False
    return "localhost" not in lowered and "127.0.0.1" not in lowered


def _qr_media_url(settings: Settings, invoice_number: str) -> str | None:
    base = (settings.public_base_url or "").rstrip("/")
    if not _is_public_https(base):
        return None
    return f"{base}/api/v1/invoices/{invoice_number}/qr.png"


def _send_meta(
    *,
    destination: str,
    caption: str,
    qr_png: bytes,
    settings: Settings,
) -> WhatsAppResult:
    if not settings.whatsapp_meta_token or not settings.whatsapp_meta_phone_number_id:
        logger.warning("whatsapp_skipped reason=meta_not_configured")
        return WhatsAppResult(status="skipped_not_configured", destination=destination)

    version = settings.whatsapp_meta_api_version.strip("/") or "v21.0"
    phone_id = settings.whatsapp_meta_phone_number_id
    headers = {"Authorization": f"Bearer {settings.whatsapp_meta_token}"}
    to = destination.lstrip("+")

    try:
        upload = httpx.post(
            f"https://graph.facebook.com/{version}/{phone_id}/media",
            headers=headers,
            files={
                "file": ("etims-qr.png", qr_png, "image/png"),
                "messaging_product": (None, "whatsapp"),
                "type": (None, "image/png"),
            },
            timeout=20.0,
        )
        upload.raise_for_status()
        media_id = upload.json().get("id")
        if not media_id:
            raise RuntimeError("Meta media upload returned no id")

        response = httpx.post(
            f"https://graph.facebook.com/{version}/{phone_id}/messages",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "image",
                "image": {"id": media_id, "caption": caption},
            },
            timeout=20.0,
        )
        response.raise_for_status()
        messages = response.json().get("messages") or []
        provider_id = messages[0].get("id") if messages else None
        logger.info("whatsapp_sent provider=meta to=%s provider_id=%s", destination, provider_id)
        return WhatsAppResult(status="sent", destination=destination, provider_id=provider_id)
    except Exception as exc:
        logger.exception("whatsapp_failed provider=meta to=%s", destination)
        return WhatsAppResult(status="failed", destination=destination, error=str(exc))


def _send_twilio(
    *,
    destination: str,
    caption: str,
    invoice_number: str,
    settings: Settings,
) -> WhatsAppResult:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("whatsapp_skipped reason=twilio_not_configured")
        return WhatsAppResult(status="skipped_not_configured", destination=destination)

    media_url = _qr_media_url(settings, invoice_number)
    if media_url is None:
        logger.warning("whatsapp_skipped reason=public_url_required invoice=%s", invoice_number)
        return WhatsAppResult(
            status="skipped_public_url_required",
            destination=destination,
            error="Twilio needs PUBLIC_BASE_URL as public HTTPS (use ngrok or Render).",
        )

    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={
                "From": settings.twilio_whatsapp_from,
                "To": f"whatsapp:{destination}",
                "Body": caption,
                "MediaUrl": media_url,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        provider_id = response.json().get("sid")
        logger.info("whatsapp_sent provider=twilio to=%s provider_id=%s", destination, provider_id)
        return WhatsAppResult(status="sent", destination=destination, provider_id=provider_id)
    except Exception as exc:
        logger.exception("whatsapp_failed provider=twilio to=%s", destination)
        return WhatsAppResult(status="failed", destination=destination, error=str(exc))


def dispatch_qr_receipt(
    *,
    phone: str | None,
    caption: str,
    qr_png: bytes,
    invoice_number: str,
    settings: Settings | None = None,
) -> WhatsAppResult:
    settings = settings or get_settings()
    destination = normalize_msisdn(phone)
    if destination is None:
        logger.warning("whatsapp_skipped reason=invalid_phone raw=%s", phone)
        return WhatsAppResult(status="skipped_invalid_phone", destination=None)

    if not qr_png:
        return WhatsAppResult(status="failed", destination=destination, error="QR image is empty")

    provider = _configured_provider(settings)
    if provider == "meta":
        return _send_meta(
            destination=destination,
            caption=caption,
            qr_png=qr_png,
            settings=settings,
        )
    if provider == "twilio":
        return _send_twilio(
            destination=destination,
            caption=caption,
            invoice_number=invoice_number,
            settings=settings,
        )

    logger.info("whatsapp_mocked to=%s invoice=%s", destination, invoice_number)
    return WhatsAppResult(status="mocked", destination=destination, provider_id="mock-local")
