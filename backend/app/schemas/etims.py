"""
File: backend/app/schemas/etims.py
Description:
    Request/response shapes for eTIMS invoice generation, listing, and OSCU verification.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.tax import TaxLineInput, TaxLineResult

TaxCategory = Literal[
    "standard",
    "zero_rated",
    "exempt",
]


class InvoiceItemCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: str = Field(min_length=1, max_length=200)
    quantity: Decimal = Field(gt=0, le=100000)
    unit_price: Decimal = Field(ge=0, le=100000000)
    tax_category: TaxCategory = "exempt"

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Description cannot be empty")
        return normalized


class CreateInvoiceRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trader_pin: Optional[str] = Field(default=None, max_length=11)
    seller_pin: Optional[str] = Field(default=None, max_length=11)
    trader_name: Optional[str] = Field(default=None, max_length=255)
    trader_phone: Optional[str] = Field(default=None, max_length=32)
    buyer_pin: Optional[str] = Field(default=None, max_length=11)
    buyer_name: Optional[str] = Field(default=None, max_length=255)
    items: List[TaxLineInput] = Field(min_length=1)
    send_sms: bool = True
    send_whatsapp: bool = True
    claimed_grand_total: Optional[Decimal] = None
    buyer_phone: Optional[str] = Field(default=None, max_length=20)
    confirmation_token: Optional[str] = Field(default=None)


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
    trader_phone: Optional[str]
    buyer_pin: Optional[str]
    buyer_name: str
    items: List[InvoiceItemResponse]
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
    sms_destination: Optional[str]
    sms_body: Optional[str]
    whatsapp_status: str
    whatsapp_destination: Optional[str]
    whatsapp_message_id: Optional[str]
    whatsapp_body: Optional[str]
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
    invoice: Optional[InvoiceResponse] = None
