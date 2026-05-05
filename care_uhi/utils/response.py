"""Beckn protocol ACK/NACK response helpers."""

from pydantic import ValidationError


def build_ack() -> dict:
    """Build a standard Beckn ACK response."""
    return {
        "message": {"ack": {"status": "ACK"}},
    }


def build_nack(error_message: str, error_type: str = "CONTEXT-ERROR", error_code: str = "30000") -> dict:
    """Build a standard Beckn NACK response with error details."""
    return {
        "message": {"ack": {"status": "NACK"}},
        "error": {
            "type": error_type,
            "code": error_code,
            "message": error_message,
        },
    }


def format_validation_errors(exc: Exception) -> str:
    """Flatten Pydantic validation errors into a single human-readable string."""
    if isinstance(exc, ValidationError):
        parts = []
        for err in exc.errors():
            loc = " → ".join(str(l) for l in err["loc"])
            parts.append(f"{loc}: {err['msg']}")
        return "; ".join(parts)
    return str(exc)
