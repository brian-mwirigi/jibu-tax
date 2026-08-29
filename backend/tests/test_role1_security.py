import hashlib
import hmac
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).parents[1]))

from app.api.v1.webhooks import router as webhook_router
from app.main import app
from app.schemas.kra import PinVerificationRequest
from app.security.replay import USED_REQUEST_IDS, reject_reused_request
from app.security.tool_dispatcher import ToolRejected, dispatch_tool
from app.security.webhooks import verify_signature


def test_pin_is_normalized() -> None:
    request = PinVerificationRequest(pin=" p051234567m ")

    assert request.pin == "P051234567M"


@pytest.mark.parametrize(
    "pin,expected",
    [
        ("invalid", "INVALID"),
        ("P123", "P123"),
        ("12345678901", "12345678901"),
        ("P051234567", "P051234567"),
        ("P051234567MM", "P051234567MM"),
    ],
)
def test_arbitrary_pin_is_accepted_and_normalized(pin: str, expected: str) -> None:
    req = PinVerificationRequest(pin=pin)
    assert req.pin == expected


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(ToolRejected):
        await dispatch_tool(
            tool_name="delete_database",
            raw_arguments={},
        )


def test_valid_signature_is_accepted() -> None:
    body = b'{"pin":"P051234567M"}'
    secret = "test-secret"
    signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    assert verify_signature(body, signature, secret)


def test_invalid_signature_is_rejected() -> None:
    assert not verify_signature(
        b'{"pin":"P051234567M"}',
        "wrong",
        "test-secret",
    )


def test_request_id_cannot_be_reused() -> None:
    request_id = "role1-test-request-001"
    USED_REQUEST_IDS.discard(request_id)

    reject_reused_request(request_id)

    with pytest.raises(ToolRejected):
        reject_reused_request(request_id)

    USED_REQUEST_IDS.discard(request_id)


def test_webhook_requires_signature() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/tools/validate-buyer",
        json={
            "tool": "verify_pin",
            "request_id": "role1-test-request-002",
            "timestamp": 1,
            "arguments": {"pin": "P051234567M"},
        },
    )

    assert response.status_code == 401