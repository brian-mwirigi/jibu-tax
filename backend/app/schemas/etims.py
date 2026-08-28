"""Request/response shapes for eTIMS invoice issue, list, and verify."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.tax import TaxLineInput, TaxLineResult


class CreateInvoiceRequest(BaseModel):
    trader_pin: str | None = Field(default=None, max_length=11)
    trader_name: str | None = Field(default=None, max_length=255)
    trader_phone: str | None = Field(default=None, max_length=32)
    buyer_pin: str | None = Field(default=None, max_length=11)
    buyer_name: str | None = Field(default=None, max_length=255)
    items: list[TaxLineInput] = Field(min_length=1)
    send_sms: bool = True
    send_whatsapp: bool = True
    claimed_grand_total: Decimal | None = None


class InvoiceItemResponse(TaxLineResult):
    pass


class InvoiceResponse(BaseModel):
    invoice_number: str
    cu_invoice_number: str
    oscu_control_code: str
    oscu_payload_hash: str
    oscu_device_id: str
    trader_pin: str
    trader_name: str
    trader_phone: str | None
    buyer_pin: str | None
    buyer_name: str
    items: list[InvoiceItemResponse]
    total_standard_amount: Decimal
    total_standard_vat: Decimal
    total_fuel_amount: Decimal
    total_fuel_tax: Decimal
    total_exempt_amount: Decimal
    total_zero_rated_amount: Decimal
    total_vat_amount: Decimal
    grand_total: Decimal
    qr_code_url: str
    qr_code_base64: str
    sms_status: str
    sms_destination: str | None
    sms_body: str | None
    whatsapp_status: str
    whatsapp_destination: str | None
    whatsapp_message_id: str | None
    whatsapp_body: str | None
    signature_valid: bool = True
    issued_at: datetime
    spoken_en: str
    spoken_sw: str


class InvoiceListItem(BaseModel):
    invoice_number: str
    buyer_name: str
    grand_total: Decimal
    oscu_control_code: str
    sms_status: str
    whatsapp_status: str
    issued_at: datetime


class VerifyInvoiceResponse(BaseModel):
    valid: bool
    message: str
    invoice: InvoiceResponse | None = None
