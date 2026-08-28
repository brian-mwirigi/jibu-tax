from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    tool: str = Field(
        min_length=1,
        max_length=100,
    )

    request_id: str = Field(
        min_length=16,
        max_length=200,
    )

    timestamp: int

    arguments: dict[str, Any]


class ToolCallResponse(BaseModel):
    success: bool
    result: dict[str, Any] | None = None
    message: str