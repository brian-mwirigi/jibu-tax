"""Month-end TOT / NIL filing endpoints (cron + manual demo trigger)."""

import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.database import get_db
from app.models.tax_return import TaxReturnFiling
from app.schemas.filing import FilingResponse, MonthEndRunRequest
from app.services.filing_engine import FilingEngine

router = APIRouter()


def _to_response(row: TaxReturnFiling) -> FilingResponse:
    return FilingResponse(
        id=row.id,
        trader_pin=row.trader_pin,
        trader_name=row.trader_name,
        tax_period_year=row.tax_period_year,
        tax_period_month=row.tax_period_month,
        return_kind=row.return_kind.value,
        status=row.status.value,
        invoice_count=row.invoice_count,
        gross_turnover=row.gross_turnover,
        tax_payable=row.tax_payable,
        kra_payload=json.loads(row.kra_payload),
        ack_number=row.ack_number,
        prn=row.prn,
        error_message=row.error_message,
    )


@router.post("/month-end", response_model=List[FilingResponse])
def run_month_end(body: MonthEndRunRequest, db: Session = Depends(get_db)) -> list[FilingResponse]:
    as_of = date.fromisoformat(body.as_of) if body.as_of else None
    filings = FilingEngine(db).run_month_end(as_of=as_of)
    return [_to_response(row) for row in filings]


@router.get("", response_model=List[FilingResponse])
def list_filings(
    db: Session = Depends(get_db),
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
) -> list[FilingResponse]:
    statement = select(TaxReturnFiling).order_by(TaxReturnFiling.filed_at.desc())
    rows = list(db.exec(statement).all())
    if year is not None:
        rows = [row for row in rows if row.tax_period_year == year]
    if month is not None:
        rows = [row for row in rows if row.tax_period_month == month]
    return [_to_response(row) for row in rows]
