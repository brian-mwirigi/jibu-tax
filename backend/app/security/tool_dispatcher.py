from typing import Any

from pydantic import ValidationError

from app.schemas.kra import PinVerificationRequest
from app.services.kra_service import KRAService


class ToolRejected(Exception):
    pass


ALLOWED_TOOLS = {
    "verify_pin",
    "submit_invoice",
}


async def dispatch_verify_pin(
    raw_arguments: dict[str, Any],
) -> dict[str, Any]:
    allowed_arguments = {
        "pin": raw_arguments.get("pin"),
    }

    try:
        request = PinVerificationRequest(
            **allowed_arguments,
        )
    except ValidationError as error:
        raise ToolRejected(
            "Invalid PIN request"
        ) from error

    result = await KRAService().verify_pin(
        request.pin,
    )

    return result.model_dump()


async def dispatch_tool(
    tool_name: str,
    raw_arguments: dict[str, Any],
) -> dict[str, Any]:
    if tool_name not in ALLOWED_TOOLS:
        raise ToolRejected(
            "Tool is not permitted"
        )

    if tool_name == "verify_pin":
        return await dispatch_verify_pin(
            raw_arguments,
        )

    if tool_name == "submit_invoice":
        raise ToolRejected(
            "Invoice submission is not implemented yet"
        )

    raise ToolRejected(
        "Unknown tool"
    )