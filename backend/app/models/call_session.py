"""Voice call audit row. Role 2 fills this; table exists so the schema is complete."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CallSession(Base):
    __tablename__ = "call_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    caller_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_commodity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extracted_quantity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_buyer_pin: Mapped[str | None] = mapped_column(String(11), nullable=True)
    pin_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoice_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoice_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sms_dispatched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
