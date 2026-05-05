
import logging

from care.emr.resources.scheduling.slot.spec import BookingStatusChoices
from care_uhi.mappers.order_mapper import map_booking_to_order
from care_uhi.models import BecknOrder
from care_uhi.resources.common import OrderState

logger = logging.getLogger(__name__)


class OnStatusService:
    """Process a Beckn status request."""

    def execute(self, context: dict, message: dict) -> dict:
        order_id = message.get("order_id", "") or message.get(
            "order", {}
        ).get("id", "")

        try:
            beckn_order = BecknOrder.objects.select_related(
                "booking",
                "booking__token_slot",
                "booking__token_slot__resource",
                "booking__token_slot__resource__facility",
                "booking__token_slot__resource__user",
                "booking__patient",
                "booking__charge_item",
            ).get(order_id=order_id)
        except BecknOrder.DoesNotExist:
            return {
                "error": {
                    "type": "DOMAIN-ERROR",
                    "code": "40000",
                    "message": f"Order {order_id} not found",
                }
            }

        # Sync status from CARE booking → Beckn order if changed
        self._sync_status(beckn_order)

        return map_booking_to_order(beckn_order)

    def _sync_status(self, beckn_order: BecknOrder) -> None:
        """Keep BecknOrder.status in sync with CARE booking status."""
        if not beckn_order.booking:
            return

        booking_status = beckn_order.booking.status
        status_map = {
            BookingStatusChoices.proposed.value: OrderState.initialized.value,
            BookingStatusChoices.pending.value: OrderState.initialized.value,
            BookingStatusChoices.booked.value: OrderState.active.value,
            BookingStatusChoices.arrived.value: OrderState.active.value,
            BookingStatusChoices.checked_in.value: OrderState.active.value,
            BookingStatusChoices.in_consultation.value: OrderState.active.value,
            BookingStatusChoices.fulfilled.value: OrderState.completed.value,
            BookingStatusChoices.noshow.value: OrderState.completed.value,
            BookingStatusChoices.cancelled.value: OrderState.cancelled.value,
            BookingStatusChoices.entered_in_error.value: OrderState.cancelled.value,
            BookingStatusChoices.rescheduled.value: OrderState.cancelled.value,
        }
        new_status = status_map.get(booking_status, beckn_order.status)

        if new_status != beckn_order.status:
            beckn_order.status = new_status
            beckn_order.save(update_fields=["status", "updated_at"])
