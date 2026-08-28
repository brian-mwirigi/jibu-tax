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
"""
File: backend/app/models/invoice.py
Description:
    eTIMS Fiscal Invoice and Line Items Models.
    - Captures official electronic tax invoices generated via OSCU engine.
    - Fields include:
        * invoice_number: Sequential eTIMS invoice number (e.g. INV-2026-00001).
        * oscu_control_code: Cryptographic control code signature.
        * oscu_device_id: KRA fiscal device identifier.
        * trader_phone: Primary identifier for informal traders (dial-in MSISDN).
        * trader_pin (Optional): Seller's KRA PIN if onboarded; otherwise mapped via reverse-invoicing or phone.
        * trader_name: Seller's trading or business name.
        * buyer_name: Buyer's name or 'Walk-in Consumer' for retail sales.
        * buyer_pin (Optional): Mandatory only for B2B transactions claiming tax deduction; OPTIONAL / None for retail consumer (B2C) sales.
        * total_taxable_amount, total_vat_amount, total_exempt_amount, grand_total.
        * qr_code_url / qr_code_base64: Official KRA verification link and QR image.
        * sms_status: Delivery state of customer SMS receipt.
    - InvoiceItem model captures individual line items, HS code, quantity, unit price, and VAT rate.
"""
