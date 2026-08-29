import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


KRA_PIN_PATTERN = re.compile(
    r"^[AP]\d{9}[A-Z]$",
    re.IGNORECASE,
)


class PinVerificationRequest(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    pin: str = Field(
        default="CONSUMER_RETAIL",
        min_length=1,
        max_length=64,
    )

    @field_validator("pin", mode="before")
    @classmethod
    def normalize_and_validate_pin(
        cls,
        value: str,
    ) -> str:
        if not value:
            return "CONSUMER_RETAIL"
        return str(value).strip().upper()


class TaxpayerResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    valid: bool
    pin: str
    taxpayer_name: str | None = None
    taxpayer_type: str | None = None
    vat_registered: bool = False
    etims_onboarded: bool = False
    message: str