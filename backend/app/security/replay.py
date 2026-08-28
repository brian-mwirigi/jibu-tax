import time

from app.security.tool_dispatcher import ToolRejected


USED_REQUEST_IDS: set[str] = set()


def verify_timestamp(
    timestamp: int,
    maximum_age_seconds: int = 300,
) -> None:
    current_time = int(time.time())

    if abs(current_time - timestamp) > maximum_age_seconds:
        raise ToolRejected(
            "Webhook request has expired"
        )


def reject_reused_request(
    request_id: str,
) -> None:
    if request_id in USED_REQUEST_IDS:
        raise ToolRejected(
            "Webhook request has already been used"
        )

    USED_REQUEST_IDS.add(request_id)