"""
Celery tasks for async Beckn request processing.

All inbound Beckn requests are dispatched here after the
immediate ACK response. Each task:
  1. Resolves the service via the action registry
  2. Executes the service
  3. Sends the /on_* callback to the BAP
  4. Updates the BecknTransaction record
"""

import logging

from celery import shared_task

from ccm_uhi.models import BecknTransaction
from ccm_uhi.outbound.sender import send_callback, send_error_callback
from ccm_uhi.registry.action_registry import get_callback_action, get_service

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def process_beckn_request(self, message_id: str):
    """
    Main async handler for all Beckn inbound actions.

    Looks up the transaction by message_id (unique per request),
    dispatches to the appropriate service, and sends the callback.
    """
    try:
        txn = BecknTransaction.objects.get(message_id=message_id)
    except BecknTransaction.DoesNotExist:
        logger.error("Transaction with message_id %s not found", message_id)
        return

    txn.status = "processing"
    txn.save(update_fields=["status", "updated_at"])

    action = txn.action
    context = {
        "transaction_id": str(txn.transaction_id),
        "message_id": str(txn.message_id),
        "action": action,
        "domain": txn.domain,
        "version": txn.version,
        "consumer_id": txn.consumer_id,
        "consumer_uri": txn.consumer_uri,
    }
    message = txn.payload.get("message", {})

    try:
        service = get_service(action)
        result = service.execute(context, message)

        callback_action = get_callback_action(action)
        logger.info(
            "Beckn %s (message_id=%s) result: %s", action, message_id, result
        )
        send_callback(
            consumer_uri=txn.consumer_uri,
            callback_action=callback_action,
            context=context,
            message=result,
        )

        txn.status = "completed"
        txn.response_payload = result
        txn.save(update_fields=["status", "response_payload", "updated_at"])

    except Exception as exc:
        logger.exception(
            "Error processing Beckn %s (message_id=%s)", action, message_id
        )

        callback_action = get_callback_action(action)
        send_error_callback(
            consumer_uri=txn.consumer_uri,
            callback_action=callback_action,
            context=context,
            error_code="50000",
            error_message=str(exc),
        )

        txn.status = "error"
        txn.error = {"type": "INTERNAL-ERROR", "message": str(exc)}
        txn.save(update_fields=["status", "error", "updated_at"])

        # Retry on transient errors
        raise self.retry(exc=exc)
