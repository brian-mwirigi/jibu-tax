"""KRA PIN verification endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.kra import PinVerificationRequest, TaxpayerResponse
from app.services.kra_service import KRAService


router = APIRouter()


@router.post(
    "/verify-pin",
    response_model=TaxpayerResponse,
)
async def verify_pin(
    payload: PinVerificationRequest,
) -> TaxpayerResponse:
    try:
        return await KRAService().verify_pin(payload.pin)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="PIN verification is temporarily unavailable",
        ) from error
