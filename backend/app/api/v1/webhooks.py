from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError

from app.config import get_settings
from app.schemas.webhook import ToolCallRequest
from app.security.replay import (
    reject_reused_request,
    verify_timestamp,
)
from app.security.tool_dispatcher import (
    ToolRejected,
    dispatch_tool,
)
from app.security.webhooks import verify_signature


router = APIRouter()


@router.post("/validate-buyer")
async def validate_buyer(
    request: Request,
    x_webhook_signature: str | None = Header(
        default=None,
    ),
) -> dict:
    if x_webhook_signature is None:
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature",
        )

    raw_body = await request.body()
    settings = get_settings()

    secret = settings.webhook_secret

    if not verify_signature(
        raw_body=raw_body,
        supplied_signature=x_webhook_signature,
        secret=secret,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    try:
        payload = ToolCallRequest.model_validate(
            await request.json(),
        )

        verify_timestamp(
            payload.timestamp,
        )

        reject_reused_request(
            payload.request_id,
        )

        result = await dispatch_tool(
            tool_name=payload.tool,
            raw_arguments=payload.arguments,
        )

        return {
            "success": True,
            "result": result,
            "message": "PIN verification completed",
        }

    except ToolRejected as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except KeyError as error:
        raise HTTPException(
            status_code=422,
            detail="Malformed webhook payload",
        ) from error

    except (ValidationError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail="Malformed webhook payload",
        ) from error