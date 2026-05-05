import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Timeout for outbound HTTP calls (connect, read) in seconds
OUTBOUND_TIMEOUT = (5, 30)


def send_callback(
    consumer_uri: str,
    callback_action: str,
    context: dict,
    message: dict,
) -> bool:
    """
    Send an /on_* callback to the BAP.

    Args:
        consumer_uri: The consumer's (BAP) base callback URL
        callback_action: e.g. "on_search", "on_init"
        context: Beckn context dict (updated with action=callback_action)
        message: The response message payload
    """
    url = f"{consumer_uri.rstrip('/')}/{callback_action}"

    callback_context = {**context, "action": callback_action}

    # Add provider (BPP) identity to context
    callback_context["provider_id"] = getattr(settings, "UHI_PROVIDER_ID", "care-hspa")
    callback_context["provider_uri"] = getattr(settings, "UHI_PROVIDER_URI", "")

    payload = {
        "context": callback_context,
        "message": message,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=OUTBOUND_TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        logger.info("Callback %s sent to %s: %s", callback_action, url, response.status_code)
        return True
    except requests.RequestException:
        logger.exception("Failed to send callback %s to %s", callback_action, url)
        return False


def send_error_callback(
    consumer_uri: str,
    callback_action: str,
    context: dict,
    error_code: str,
    error_message: str,
) -> bool:
    """Send an error response callback to the consumer (BAP)."""
    message = {
        "error": {
            "type": "DOMAIN-ERROR",
            "code": error_code,
            "message": error_message,
        }
    }
    return send_callback(consumer_uri, callback_action, context, message)
