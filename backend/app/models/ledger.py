"""
Immutable sales ledger.

Every successful voice or API transaction is appended once. Application code never
updates or deletes rows; PostgreSQL also rejects UPDATE/DELETE via trigger.
A SHA-256 hash chain binds each row to the previous entry.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Index, Numeric, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class LedgerEntry(SQLModel, table=True):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_ledger_invoice_number"),
        UniqueConstraint("sequence", name="uq_ledger_sequence"),
        Index(
            "ix_ledger_trader_period",
            "trader_pin",
            "tax_period_year",
            "tax_period_month",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sequence: int = Field(unique=True, index=True)
    posted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    trader_pin: str = Field(index=True, max_length=11)
    trader_name: str
    buyer_pin: Optional[str] = None
    buyer_name: Optional[str] = None
    invoice_number: str = Field(index=True)
    call_session_id: Optional[str] = Field(default=None, index=True)
    taxable_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    vat_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    grand_total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    currency: str = Field(default="KES", max_length=3)
    tax_period_year: int = Field(index=True)
    tax_period_month: int = Field(index=True)
    source: str = Field(default="voice_call")
    transaction_payload: str = Field(sa_column=Column(Text, nullable=False))
    prev_hash: str = Field(max_length=64)
    entry_hash: str = Field(max_length=64, index=True)
    celery_task_id: Optional[str] = None
