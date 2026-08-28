"""Celery tasks that persist successful transactions without stalling the live call."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlmodel import Session

from app.celery_app import celery_app
from app.database import engine
from app.services.ledger_service import LedgerService


@celery_app.task(
    bind=True,
    name="ledger.persist_successful_transaction",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def persist_successful_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
    with Session(engine) as session:
        entry = LedgerService(session).append_successful_transaction(
            trader_pin=payload["trader_pin"],
            trader_name=payload["trader_name"],
            invoice_number=payload["invoice_number"],
            grand_total=Decimal(str(payload["grand_total"])),
            taxable_amount=Decimal(str(payload["taxable_amount"])),
            vat_amount=Decimal(str(payload["vat_amount"])),
            buyer_pin=payload.get("buyer_pin"),
            buyer_name=payload.get("buyer_name"),
            call_session_id=payload.get("call_session_id"),
            source=payload.get("source", "voice_call"),
            extra=payload.get("extra"),
            celery_task_id=self.request.id,
        )
        return {
            "id": str(entry.id),
            "invoice_number": entry.invoice_number,
            "entry_hash": entry.entry_hash,
            "sequence": entry.sequence,
        }


def enqueue_ledger_write(payload: dict[str, Any]) -> Optional[str]:
    """
    Fire-and-forget from the voice webhook.

    If Redis is unreachable, fall back to a synchronous write so the sale is
    never lost — the call path still returns immediately after this function
    unless the fallback is used.
    """
    try:
        result = persist_successful_transaction.delay(payload)
        return result.id
    except Exception:
        with Session(engine) as session:
            LedgerService(session).append_successful_transaction(
                trader_pin=payload["trader_pin"],
                trader_name=payload["trader_name"],
                invoice_number=payload["invoice_number"],
                grand_total=Decimal(str(payload["grand_total"])),
                taxable_amount=Decimal(str(payload["taxable_amount"])),
                vat_amount=Decimal(str(payload["vat_amount"])),
                buyer_pin=payload.get("buyer_pin"),
                buyer_name=payload.get("buyer_name"),
                call_session_id=payload.get("call_session_id"),
                source=payload.get("source", "voice_call"),
                extra=payload.get("extra"),
            )
        return None
