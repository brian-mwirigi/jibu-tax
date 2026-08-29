"""SMS receipt dispatch. Mock by default; Africa's Talking when keys are set."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

KENYA_MSISDN = re.compile(r"^(?:\+?254|0)7\d{8}$")


@dataclass
class SmsResult:
    status: str
    destination: str | None
    provider_id: str | None = None
    error: str | None = None


def money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):,.2f}"


def format_receipt_sms(
    *,
    invoice_number: str,
    buyer_name: str,
    grand_total: Decimal,
    vat_amount: Decimal,
    control_code: str,
    verify_url: str,
) -> str:
    return (
        f"JibuTax eTIMS\n"
        f"INV {invoice_number}\n"
        f"Buyer: {buyer_name}\n"
        f"Total KES {money_text(grand_total)}\n"
        f"VAT KES {money_text(vat_amount)}\n"
        f"Code {control_code}\n"
        f"{verify_url}"
    )


def normalize_msisdn(phone: str | None) -> str | None:
    if not phone:
        return None
    compact = re.sub(r"[\s-]", "", phone.strip())
    if compact.startswith("+"):
        compact = compact[1:]
    if compact.startswith("07") and len(compact) == 10:
        compact = "254" + compact[1:]
    if compact.startswith("7") and len(compact) == 9:
        compact = "254" + compact
    if not re.fullmatch(r"2547\d{8}", compact):
        return None
    return "+" + compact


def dispatch_receipt(phone: str | None, body: str, settings: Settings | None = None) -> SmsResult:
    settings = settings or get_settings()
    destination = normalize_msisdn(phone)
    if destination is None:
        logger.warning("sms_skipped reason=invalid_phone raw=%s", phone)
        return SmsResult(status="skipped_invalid_phone", destination=None)

    provider = (settings.sms_provider or "mock").lower()
    if provider != "africastalking" or not settings.africastalking_api_key:
        logger.info("sms_mocked to=%s invoice_sms=1", destination)
        return SmsResult(status="mocked", destination=destination, provider_id="mock-local")

    try:
        response = httpx.post(
            "https://api.africastalking.com/version1/messaging",
            headers={
                "apiKey": settings.africastalking_api_key,
                "Accept": "application/json",
            },
            data={
                "username": settings.africastalking_username,
                "to": destination,
                "message": body,
                "from": settings.africastalking_sender_id or "JIBUTAX",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        recipients = payload.get("SMSMessageData", {}).get("Recipients") or []
        provider_id = recipients[0].get("messageId") if recipients else None
        logger.info("sms_sent to=%s provider_id=%s", destination, provider_id)
        return SmsResult(status="sent", destination=destination, provider_id=provider_id)
    except Exception as exc:
        logger.exception("sms_failed to=%s", destination)
        return SmsResult(status="failed", destination=destination, error=str(exc))
