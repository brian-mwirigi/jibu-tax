import hashlib
import hmac


def verify_signature(
    raw_body: bytes,
    supplied_signature: str,
    secret: str,
) -> bool:
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        supplied_signature,
    )
