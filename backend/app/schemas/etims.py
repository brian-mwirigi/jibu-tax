from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TaxCategory = Literal[
    "standard",
    "zero_rated",
    "exempt",
]


class InvoiceItemCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    description: str = Field(
        min_length=1,
        max_length=200,
    )

    quantity: Decimal = Field(
        gt=0,
        le=100000,
    )

    unit_price: Decimal = Field(
        ge=0,
        le=100000000,
    )

    tax_category: TaxCategory

    @field_validator("description")
    @classmethod
    def clean_description(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "Description cannot be empty"
            )

        return normalized


class CreateInvoiceRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    seller_pin: str = Field(
        min_length=11,
        max_length=11,
    )

    buyer_pin: str = Field(
        min_length=11,
        max_length=11,
    )

    items: list[InvoiceItemCreate] = Field(
        min_length=1,
        max_length=100,
    )

    send_sms: bool = False

    buyer_phone: str | None = Field(
        default=None,
        max_length=20,
    )

    confirmation_token: str = Field(
        min_length=32,
        max_length=200,
    )