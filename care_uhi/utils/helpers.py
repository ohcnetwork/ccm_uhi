"""Helper functions for Beckn transaction management."""

from care_uhi.models import BecknTransaction
from care_uhi.resources.common import BecknAction, TransactionStatus

TERMINAL_ACTIONS = {
    BecknAction.cancel.value,
}


class TransactionClosedError(Exception):
    """Raised when a transaction lifecycle is already closed."""

    pass


def check_transaction_not_closed(transaction_id: str) -> None:
    """Raise if this transaction has a terminal action (cancel) completed."""
    closed = BecknTransaction.objects.filter(
        transaction_id=transaction_id,
        action__in=TERMINAL_ACTIONS,
        status=TransactionStatus.completed.value,
    ).exists()
    if closed:
        msg = f"Transaction {transaction_id} is already closed and cannot accept new requests"
        raise TransactionClosedError(msg)




def update_or_create_transaction(context: dict, action: str, payload: dict):
    """Create or update a BecknTransaction from context and action."""
    if action !=  BecknAction.status.value:
        check_transaction_not_closed(context["transaction_id"])

    return BecknTransaction.objects.update_or_create(
        transaction_id=context["transaction_id"],
        action=action,
        defaults={
            "message_id": context["message_id"],
            "consumer_id": context["consumer_id"],
            "consumer_uri": context["consumer_uri"],
            "domain": context.get("domain", "nic2004:85111"),
            "version": context.get("version", "1.1.0"),
            "payload": payload,
            "status": TransactionStatus.received.value,
        },
    )
