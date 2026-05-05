import logging

from care.emr.models.scheduling.booking import TokenBooking
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices

logger = logging.getLogger(__name__)


class OnConfirmService:
    """Confirm a booking by updating its status."""

    def execute(self, context: dict, message: dict) -> dict:
        booking_id = message.get("booking_id", "")
        if not booking_id:
            msg = "booking_id is required"
            raise ValueError(msg)

        try:
            booking = TokenBooking.objects.select_related(
                "token_slot",
                "token_slot__resource",
                "token_slot__resource__facility",
                "token_slot__availability",
                "token_slot__availability__schedule",
                "patient",
            ).get(external_id=booking_id)
        except TokenBooking.DoesNotExist:
            msg = f"Booking {booking_id} not found"
            raise ValueError(msg)

        if booking.status in (BookingStatusChoices.cancelled.value, BookingStatusChoices.fulfilled.value):
            msg = f"Booking is already '{booking.status}' and cannot be confirmed"
            raise ValueError(msg)

        booking.status = BookingStatusChoices.booked.value
        booking.save(update_fields=["status", "modified_date"])

        return self._build_response(booking)

    def _build_response(self, booking: TokenBooking) -> dict:
        from ccm_uhi.mappers.catalog_mapper import map_facility_to_provider, map_slot_to_fulfillment
        from ccm_uhi.mappers.order_mapper import map_patient_to_billing

        result = {
            "booking_id": str(booking.external_id),
            "status": booking.status,
            "patient": map_patient_to_billing(booking.patient),
        }

        slot = booking.token_slot
        if slot:
            resource = slot.resource
            result["provider"] = map_facility_to_provider(resource.facility)
            result["fulfillment"] = map_slot_to_fulfillment(slot, resource)

        return result
