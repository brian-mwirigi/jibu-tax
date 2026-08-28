"""
Append-only ledger service.

Callers on the voice path must not wait on this — enqueue via Celery.
This module owns hash-chain construction and period bucketing for TOT aggregation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.ledger import LedgerEntry

GENESIS_HASH = "0" * 64
MONEY = Decimal("0.01")


def money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def tax_period_for(moment: Optional[datetime] = None) -> tuple[int, int]:
    when = moment or datetime.now(timezone.utc)
    return when.year, when.month


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(prev_hash: str, canonical_payload: str) -> str:
    material = f"{prev_hash}|{canonical_payload}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class LedgerService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def next_sequence(self) -> int:
        current = self.session.exec(select(func.max(LedgerEntry.sequence))).one()
        return int(current or 0) + 1

    def latest_hash(self) -> str:
        statement = select(LedgerEntry.entry_hash).order_by(LedgerEntry.sequence.desc()).limit(1)
        result = self.session.exec(statement).first()
        return result or GENESIS_HASH

    def get_by_invoice(self, invoice_number: str) -> Optional[LedgerEntry]:
        statement = select(LedgerEntry).where(LedgerEntry.invoice_number == invoice_number)
        return self.session.exec(statement).first()

    def append_successful_transaction(
        self,
        *,
        trader_pin: str,
        trader_name: str,
        invoice_number: str,
        grand_total: Decimal,
        taxable_amount: Decimal,
        vat_amount: Decimal,
        buyer_pin: Optional[str] = None,
        buyer_name: Optional[str] = None,
        call_session_id: Optional[str] = None,
        source: str = "voice_call",
        extra: Optional[dict[str, Any]] = None,
        celery_task_id: Optional[str] = None,
        posted_at: Optional[datetime] = None,
    ) -> LedgerEntry:
        existing = self.get_by_invoice(invoice_number)
        if existing:
            return existing

        posted_at = posted_at or datetime.now(timezone.utc)
        year, month = tax_period_for(posted_at)
        payload = {
            "trader_pin": trader_pin,
            "trader_name": trader_name,
            "buyer_pin": buyer_pin,
            "buyer_name": buyer_name,
            "invoice_number": invoice_number,
            "call_session_id": call_session_id,
            "taxable_amount": str(money(taxable_amount)),
            "vat_amount": str(money(vat_amount)),
            "grand_total": str(money(grand_total)),
            "currency": "KES",
            "tax_period_year": year,
            "tax_period_month": month,
            "source": source,
            "posted_at": posted_at.isoformat(),
            **(extra or {}),
        }
        canonical = canonical_json(payload)
        prev_hash = self.latest_hash()
        entry = LedgerEntry(
            sequence=self.next_sequence(),
            trader_pin=trader_pin.upper(),
            trader_name=trader_name,
            buyer_pin=buyer_pin.upper() if buyer_pin else None,
            buyer_name=buyer_name,
            invoice_number=invoice_number,
            call_session_id=call_session_id,
            taxable_amount=money(taxable_amount),
            vat_amount=money(vat_amount),
            grand_total=money(grand_total),
            tax_period_year=year,
            tax_period_month=month,
            source=source,
            transaction_payload=canonical,
            prev_hash=prev_hash,
            entry_hash=compute_entry_hash(prev_hash, canonical),
            celery_task_id=celery_task_id,
            posted_at=posted_at,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def aggregate_sales(self, trader_pin: str, year: int, month: int) -> dict[str, Any]:
        statement = select(
            func.count(LedgerEntry.id),
            func.coalesce(func.sum(LedgerEntry.grand_total), 0),
            func.coalesce(func.sum(LedgerEntry.vat_amount), 0),
            func.coalesce(func.sum(LedgerEntry.taxable_amount), 0),
        ).where(
            LedgerEntry.trader_pin == trader_pin.upper(),
            LedgerEntry.tax_period_year == year,
            LedgerEntry.tax_period_month == month,
        )
        count, gross, vat, taxable = self.session.exec(statement).one()
        return {
            "invoice_count": int(count or 0),
            "gross_turnover": money(gross or 0),
            "vat_amount": money(vat or 0),
            "taxable_amount": money(taxable or 0),
        }
