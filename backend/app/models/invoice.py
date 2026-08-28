"""eTIMS fiscal invoice records. Ledger posts reference invoice_number, not a hard FK."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Numeric, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    invoice_number: str = Field(index=True)
    oscu_control_code: Optional[str] = None
    oscu_device_id: Optional[str] = None
    trader_pin: str = Field(index=True)
    trader_name: str
    trader_phone: Optional[str] = None
    buyer_pin: Optional[str] = None
    buyer_name: Optional[str] = None
    total_taxable_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    total_vat_amount: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    total_exempt_amount: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(Numeric(18, 2), nullable=False)
    )
    grand_total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    qr_code_url: Optional[str] = None
    qr_code_base64: Optional[str] = None
    sms_status: str = "PENDING"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    items: list["InvoiceItem"] = Relationship(back_populates="invoice")


class InvoiceItem(SQLModel, table=True):
    __tablename__ = "invoice_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    invoice_id: UUID = Field(foreign_key="invoices.id", index=True)
    description: str
    hs_code: Optional[str] = None
    quantity: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    unit_price: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    vat_rate: Decimal = Field(sa_column=Column(Numeric(6, 4), nullable=False))
    line_total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))

    invoice: Optional[Invoice] = Relationship(back_populates="items")
