"""Audit of month-end TOT and NIL filings submitted to KRA."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Numeric, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class ReturnKind(str, Enum):
    TOT = "TOT"
    NIL = "NIL"


class FilingStatus(str, Enum):
    PENDING = "PENDING"
    FILED = "FILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class TaxReturnFiling(SQLModel, table=True):
    __tablename__ = "tax_return_filings"
    __table_args__ = (
        UniqueConstraint(
            "trader_pin",
            "tax_period_year",
            "tax_period_month",
            name="uq_filing_pin_period",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trader_pin: str = Field(index=True, max_length=11)
    trader_name: str
    tax_period_year: int = Field(index=True)
    tax_period_month: int
    return_kind: ReturnKind
    status: FilingStatus = Field(default=FilingStatus.PENDING)
    invoice_count: int = 0
    gross_turnover: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(Numeric(18, 2), nullable=False)
    )
    tax_rate: Decimal = Field(
        default=Decimal("0.0000"), sa_column=Column(Numeric(6, 4), nullable=False)
    )
    tax_payable: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(Numeric(18, 2), nullable=False)
    )
    kra_payload: str = Field(sa_column=Column(Text, nullable=False))
    kra_response: Optional[str] = Field(default=None, sa_column=Column(Text))
    ack_number: Optional[str] = None
    prn: Optional[str] = None
    error_message: Optional[str] = None
    filed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
