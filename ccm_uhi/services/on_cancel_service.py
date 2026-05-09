"""
OnCancelService: Cancel a booking.

Reuses CARE's cancel_appointment_handler to cancel the booking.
"""

import logging

from care.emr.api.viewsets.scheduling.booking import TokenBookingViewSet
from care.emr.models.scheduling.booking import TokenBooking
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices

logger = logging.getLogger(__name__)


class OnCancelService:
    """Cancel a booking."""

    def execute(self, context: dict, message: dict) -> dict:
        order_id = message.get("order_id", "")
        if not order_id:
            msg = "order_id is required"
            raise ValueError(msg)

        try:
            booking = TokenBooking.objects.select_related(
                "token_slot",
                "token_slot__resource",
                "token_slot__resource__facility",
                "token_slot__availability",
                "token_slot__availability__schedule",
                "patient",
            ).get(external_id=order_id)
        except TokenBooking.DoesNotExist:
            msg = f"Order {order_id} not found"
            raise ValueError(msg)

        if booking.status in (BookingStatusChoices.cancelled.value, BookingStatusChoices.fulfilled.value):
            msg = f"Booking is already '{booking.status}' and cannot be cancelled"
            raise ValueError(msg)

        TokenBookingViewSet.cancel_appointment_handler(
            instance=booking,
            request_data={
                "reason": BookingStatusChoices.cancelled.value,
                "note": "Cancelled via CCM UHI",
            },
            user=None,
        )

        booking.refresh_from_db()
        return self._build_response(booking)

    def _build_response(self, booking: TokenBooking) -> dict:
        from ccm_uhi.mappers.catalog_mapper import map_facility_to_provider, map_slot_to_fulfillment
        from ccm_uhi.mappers.order_mapper import map_patient_to_billing

        result = {
            "order_id": str(booking.external_id),
            "status": booking.status,
            "patient": map_patient_to_billing(booking.patient),
        }

        slot = booking.token_slot
        if slot:
            resource = slot.resource
            result["provider"] = map_facility_to_provider(resource.facility)
            result["fulfillment"] = map_slot_to_fulfillment(slot, resource)

        return result
