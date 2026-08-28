"""KRA taxpayer registry row (used by PIN checks and invoice seller/buyer lookup)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Taxpayer(Base):
    __tablename__ = "taxpayers"

    pin: Mapped[str] = mapped_column(String(11), primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trading_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    taxpayer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="INDIVIDUAL")
    vat_registered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    etims_onboarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
