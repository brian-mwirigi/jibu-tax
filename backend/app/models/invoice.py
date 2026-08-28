"""eTIMS fiscal invoice and line items persisted after OSCU signing."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    cu_invoice_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    oscu_control_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    oscu_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_payload: Mapped[str] = mapped_column(Text, nullable=False)
    oscu_device_id: Mapped[str] = mapped_column(String(64), nullable=False)

    trader_pin: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    trader_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trader_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    buyer_pin: Mapped[str | None] = mapped_column(String(11), nullable=True, index=True)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="WALK-IN CUSTOMER")

    total_standard_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_standard_vat: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_fuel_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_fuel_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_exempt_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_zero_rated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    qr_code_url: Mapped[str] = mapped_column(String(512), nullable=False)
    qr_code_base64: Mapped[str] = mapped_column(Text, nullable=False)

    sms_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    sms_destination: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sms_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    whatsapp_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    whatsapp_destination: Mapped[str | None] = mapped_column(String(32), nullable=True)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    whatsapp_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    hs_code: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_class: Mapped[str] = mapped_column(String(32), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="items")
