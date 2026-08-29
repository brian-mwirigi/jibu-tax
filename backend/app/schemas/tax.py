"""Request/response shapes for deterministic tax calculation."""

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class TaxClassification(str, Enum):
    STANDARD_16 = "STANDARD_16"
    FUEL_8 = "FUEL_8"
    EXEMPT = "EXEMPT"
    ZERO_RATED = "ZERO_RATED"


class TaxLineInput(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(gt=0, le=Decimal("1000000"))
    unit_price: Decimal = Field(ge=0, le=Decimal("1000000000"))
    claimed_line_total: Decimal | None = None
    hs_code: str | None = Field(default=None, max_length=16)


class TaxLineResult(BaseModel):
    description: str
    hs_code: str
    quantity: Decimal
    unit_price: Decimal
    tax_class: TaxClassification
    tax_rate: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal
    schedule: str


class TaxBreakdown(BaseModel):
    lines: list[TaxLineResult]
    total_standard_amount: Decimal
    total_standard_vat: Decimal
    total_fuel_amount: Decimal
    total_fuel_tax: Decimal
    total_exempt_amount: Decimal
    total_zero_rated_amount: Decimal
    total_vat_amount: Decimal
    grand_total: Decimal
    spoken_en: str
    spoken_sw: str
