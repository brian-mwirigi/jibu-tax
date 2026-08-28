"""Voice identity: look up a trader by phone, enroll KRA PIN on first call only."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.database import get_db
from app.models.taxpayer import Taxpayer

router = APIRouter()


class TaxpayerIdentityResponse(BaseModel):
    phone: str
    known: bool
    needs_trader_pin: bool
    just_enrolled: bool = False
    trader_pin: Optional[str] = None
    trader_name: Optional[str] = None
    spoken_prompt: Optional[str] = None


class EnrollPinRequest(BaseModel):
    phone: str
    pin: str = Field(min_length=11, max_length=11)
    language: str = "sw"
    legal_name: Optional[str] = None


@router.get("/identity", response_model=TaxpayerIdentityResponse)
def get_identity_by_phone(
    phone: str = Query(..., description="Caller MSISDN from the voice trunk"),
    language: str = Query(default="sw"),
    db: Session = Depends(get_db),
) -> TaxpayerIdentityResponse:
    """ElevenLabs / voice start: if this phone already has a PIN, do not ask again."""
    identity = Taxpayer.resolve_for_voice(db, phone=phone, transcript="", language=language)
    return TaxpayerIdentityResponse(
        phone=Taxpayer.normalize_phone(phone),
        known=bool(identity["known"]),
        needs_trader_pin=bool(identity["needs_trader_pin"]),
        just_enrolled=bool(identity["just_enrolled"]),
        trader_pin=identity.get("trader_pin"),
        trader_name=identity.get("trader_name"),
        spoken_prompt=identity.get("spoken_prompt"),
    )


@router.post("/enroll", response_model=TaxpayerIdentityResponse)
def enroll_pin(body: EnrollPinRequest, db: Session = Depends(get_db)) -> TaxpayerIdentityResponse:
    taxpayer = Taxpayer.link_pin_to_phone(
        db, phone=body.phone, pin=body.pin, legal_name=body.legal_name
    )
    return TaxpayerIdentityResponse(
        phone=taxpayer.phone or Taxpayer.normalize_phone(body.phone),
        known=True,
        needs_trader_pin=False,
        just_enrolled=True,
        trader_pin=taxpayer.pin,
        trader_name=taxpayer.legal_name,
        spoken_prompt=taxpayer.returning_caller_prompt(body.language),
    )
