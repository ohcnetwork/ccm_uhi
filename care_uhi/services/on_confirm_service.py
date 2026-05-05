
import logging

from django.db import transaction

from care_uhi.mappers.order_mapper import map_booking_to_order
from care_uhi.models import BecknOrder
from care_uhi.resources.common import OrderState, TermsState, TERMINAL_ORDER_STATES

logger = logging.getLogger(__name__)
VALID_TERM_STATES = {TermsState.agreed.value, TermsState.rejected.value}


class OnConfirmService:
    """Process a Beckn confirm request: validate terms + update order status."""

    def execute(self, context: dict, message: dict) -> dict:

        order_id = message.get("order_id", "")
        terms = message.get("terms", [])
        if not order_id:
            msg = "Order ID is required for confirm"
            raise ValueError(msg)
        if not terms:
            msg = "At least one term is required for confirm"
            raise ValueError(msg)

        beckn_order = self._resolve_order(order_id)

        if beckn_order.status in TERMINAL_ORDER_STATES:
            msg = f"Order is already '{beckn_order.status}' and cannot be modified"
            raise ValueError(msg)

        with transaction.atomic():
            beckn_order.status = OrderState.active.value
            beckn_order.terms = terms
            beckn_order.save(update_fields=["status", "terms", "updated_at"])

        beckn_order.refresh_from_db()
        return map_booking_to_order(beckn_order)

    def _resolve_order(self, order_id: str) -> BecknOrder:
        try:
            return BecknOrder.objects.select_related(
                "booking",
                "booking__token_slot",
                "booking__token_slot__resource",
                "booking__token_slot__resource__facility",
                "booking__token_slot__availability",
                "booking__token_slot__availability__schedule",
                "booking__patient",
            ).get(order_id=order_id)
        except BecknOrder.DoesNotExist:
            msg = f"Order {order_id} not found"
            raise ValueError(msg)
