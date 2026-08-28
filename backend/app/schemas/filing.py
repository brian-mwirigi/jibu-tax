"""Pydantic schemas for the immutable ledger and month-end filings."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LedgerEnqueueRequest(BaseModel):
    trader_pin: str = Field(min_length=11, max_length=11)
    trader_name: str
    invoice_number: str
    grand_total: Decimal
    taxable_amount: Decimal
    vat_amount: Decimal
    buyer_pin: Optional[str] = None
    buyer_name: Optional[str] = None
    call_session_id: Optional[str] = None
    source: str = "voice_call"
    extra: Optional[dict[str, Any]] = None


class LedgerEnqueueResponse(BaseModel):
    accepted: bool
    celery_task_id: Optional[str] = None
    invoice_number: str
    message: str


class LedgerEntryResponse(BaseModel):
    id: UUID
    sequence: int
    posted_at: datetime
    trader_pin: str
    invoice_number: str
    grand_total: Decimal
    tax_period_year: int
    tax_period_month: int
    prev_hash: str
    entry_hash: str


class MonthEndRunRequest(BaseModel):
    as_of: Optional[str] = Field(
        default=None,
        description="ISO date (YYYY-MM-DD). Defaults to today. Files the previous calendar month.",
    )


class FilingResponse(BaseModel):
    id: UUID
    trader_pin: str
    trader_name: str
    tax_period_year: int
    tax_period_month: int
    return_kind: str
    status: str
    invoice_count: int
    gross_turnover: Decimal
    tax_payable: Decimal
    kra_payload: dict[str, Any]
    ack_number: Optional[str] = None
    prn: Optional[str] = None
    error_message: Optional[str] = None
