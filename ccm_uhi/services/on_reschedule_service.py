"""
OnRescheduleService: Reschedule a booking to a new slot.

Cancels the existing booking and creates a new appointment
for the new fulfillment (slot) ID.
"""

import logging

from care.emr.api.viewsets.scheduling.booking import TokenBookingViewSet
from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices

from ccm_uhi.services.on_confirm_service import OnConfirmService
from ccm_uhi.mappers.order_mapper import map_patient_to_billing

logger = logging.getLogger(__name__)


class OnRescheduleService:
    """Cancel an existing booking and create a new one on a different slot."""

    def execute(self, context: dict, message: dict) -> dict:
        order_id = message.get("order_id")
        new_fulfillment_id = message.get("fulfillment_id")

        if not order_id:
            msg = "order_id is required"
            raise ValueError(msg)
        if not new_fulfillment_id:
            msg = "fulfillment_id is required"
            raise ValueError(msg)

        # --- Step 1: Resolve existing booking ---
        booking = self._resolve_booking(order_id)
        if booking.status in (
            BookingStatusChoices.cancelled.value,
            BookingStatusChoices.fulfilled.value,
        ):
            msg = f"Booking is already '{booking.status}' and cannot be rescheduled"
            raise ValueError(msg)

        new_slot = self._resolve_slot(new_fulfillment_id)

        current_slot = booking.token_slot
        if current_slot.id == new_slot.id:
            msg = "New fulfillment_id is the same as the current one. Choose a different slot."
            raise ValueError(msg)

        # --- Step 3: Resolve the new slot ---

        if new_slot.resource.facility_id != current_slot.resource.facility_id:
            msg = "New slot does not belong to the same facility"
            raise ValueError(msg)

        TokenBookingViewSet.cancel_appointment_handler(
            instance=booking,
            request_data={
                "reason": BookingStatusChoices.rescheduled.value,
                "note": "Rescheduled via CCM UHI",
            },
            user=None,
        )

        # --- Step 5: Create new booking via OnConfirmService ---
        facility = new_slot.resource.facility
        patient_data = map_patient_to_billing(booking.patient)
        note = message.get("note", "Rescheduled via CCM UHI")

        return OnConfirmService().execute(
            context,
            {
                "order": {
                    "provider_id": str(facility.external_id),
                    "fulfillment_id": str(new_fulfillment_id),
                    "billing": patient_data,
                    "note": note,
                }
            },
        )

    def _resolve_booking(self, order_id: str) -> TokenBooking:
        try:
            return TokenBooking.objects.select_related(
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

    def _resolve_slot(self, fulfillment_id: str) -> TokenSlot:
        try:
            return TokenSlot.objects.select_related(
                "resource",
                "resource__user",
                "resource__facility",
                "availability",
                "availability__schedule",
                "availability__schedule__charge_item_definition",
            ).get(external_id=fulfillment_id, deleted=False)
        except TokenSlot.DoesNotExist:
            msg = f"Slot {fulfillment_id} not found"
            raise ValueError(msg)
