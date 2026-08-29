"""Voice call audit log. Ledger writes are queued after hangup using session_id."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Numeric, Text
from sqlmodel import Field, SQLModel


class CallSession(SQLModel, table=True):
    __tablename__ = "call_sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str = Field(index=True, unique=True)
    caller_phone: str = Field(index=True)
    duration_seconds: Optional[int] = None
    language: Optional[str] = None
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))
    extracted_commodity: Optional[str] = None
    extracted_quantity: Optional[Decimal] = Field(
        default=None, sa_column=Column(Numeric(18, 4), nullable=True)
    )
    extracted_price: Optional[Decimal] = Field(
        default=None, sa_column=Column(Numeric(18, 4), nullable=True)
    )
    extracted_buyer_pin: Optional[str] = None
    pin_verified: bool = False
    invoice_generated: bool = False
    invoice_number: Optional[str] = None
    sms_dispatched: bool = False
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
