"""Celery task wrapper for the 18th-of-month TOT / NIL filing cron."""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session

from app.celery_app import celery_app
from app.database import engine
from app.services.filing_engine import FilingEngine


@celery_app.task(name="filing.run_month_end")
def run_month_end_task(as_of_iso: Optional[str] = None) -> list[dict[str, Any]]:
    from datetime import date

    as_of = date.fromisoformat(as_of_iso) if as_of_iso else None
    with Session(engine) as session:
        filings = FilingEngine(session).run_month_end(as_of=as_of)
        return [
            {
                "id": str(row.id),
                "trader_pin": row.trader_pin,
                "return_kind": row.return_kind.value,
                "status": row.status.value,
                "gross_turnover": str(row.gross_turnover),
                "ack_number": row.ack_number,
                "tax_period": f"{row.tax_period_year}-{row.tax_period_month:02d}",
            }
            for row in filings
        ]
