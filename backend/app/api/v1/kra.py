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
    from app.api.v1.stats import record_telemetry_event
    try:
        res = await KRAService().verify_pin(payload.pin)
        record_telemetry_event("KRA_REGISTRY", f"PIN Verified: {res.pin} -> {res.legal_name} ({res.status.value})", "success")
        return res
    except Exception as error:
        record_telemetry_event("KRA_REGISTRY", f"PIN Verification failed: {payload.pin}", "error")
        raise HTTPException(
            status_code=503,
            detail="PIN verification is temporarily unavailable",
        ) from error
