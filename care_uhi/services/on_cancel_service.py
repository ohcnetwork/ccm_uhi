"""
OnCancelService: Handles Beckn /cancel request.

Reuses CARE's cancel_appointment_handler to cancel the booking
and returns the updated Beckn order.
"""

import logging

from care.emr.api.viewsets.scheduling.booking import TokenBookingViewSet
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices
from care_uhi.mappers.order_mapper import map_booking_to_order
from care_uhi.models import BecknOrder
from care_uhi.resources.common import OrderState, TERMINAL_ORDER_STATES

logger = logging.getLogger(__name__)


class OnCancelService:
    """Process a Beckn cancel request."""

    def execute(self, context: dict, message: dict) -> dict:
        order_id = message.get("order_id")
        try:
            beckn_order = BecknOrder.objects.select_related(
                "booking",
                "booking__token_slot",
                "booking__token_slot__resource",
                "booking__token_slot__resource__facility",
                "booking__token_slot__availability",
                "booking__token_slot__availability__schedule",
                "booking__patient",
            ).get(order_id=order_id)
        except BecknOrder.DoesNotExist:
            return {
                "error": {
                    "type": "DOMAIN-ERROR",
                    "code": "40000",
                    "message": f"Order {order_id} not found",
                }
            }

        if beckn_order.status in TERMINAL_ORDER_STATES:
            return {
                "error": {
                    "type": "DOMAIN-ERROR",
                    "code": "40002",
                    "message": f"Order is already '{beckn_order.status}' and cannot be modified",
                }
            }

        booking = beckn_order.booking
        if not booking:
            return {
                "error": {
                    "type": "DOMAIN-ERROR",
                    "code": "40001",
                    "message": "No booking linked to this order",
                }
            }

        TokenBookingViewSet.cancel_appointment_handler(
            instance=booking,
            request_data={
                "reason": BookingStatusChoices.cancelled.value,
                "note": "Cancelled via Beckn protocol",
            },
            user=None,
        )

        beckn_order.status = OrderState.cancelled.value
        beckn_order.save(update_fields=["status", "updated_at"])
        return map_booking_to_order(beckn_order)
