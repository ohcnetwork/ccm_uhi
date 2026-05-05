import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from care.emr.models.scheduling.booking import TokenBooking
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices
from care.emr.resources.scheduling.token.spec import TokenStatusOptions
from care.utils.lock import Lock
from care.emr.models.scheduling.token import Token, TokenCategory, TokenQueue

logger = logging.getLogger(__name__)


class OnConfirmService:
    """Confirm a booking by creating a token and updating status."""

    def execute(self, context: dict, message: dict) -> dict:
        booking_id = message.get("booking_id", "")
        note = message.get("note", "")

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

        # Compute token date from slot start
        if booking.token :
            msg = "Booking already has a token and cannot be confirmed again"
            raise ValueError(msg)
        
        token_date = timezone.make_naive(
            booking.token_slot.start_datetime + timedelta(seconds=1)
        ).date()

        facility = booking.token_slot.resource.facility
        resource = booking.token_slot.resource

        filters = {
            "facility": facility,
            "resource": resource,
            "date": token_date,
        }

        # Resolve or create system-generated queue
        queue_exists = TokenQueue.objects.filter(**filters).exists()
        system_filters = {**filters, "system_generated": True}
        queue = TokenQueue.objects.filter(**system_filters).first()
        if not queue:
            create_filters = {**filters, "name": "System Generated", "system_generated": True}
            if not queue_exists:
                create_filters["is_primary"] = True
            queue = TokenQueue.objects.create(**create_filters)

        # Resolve or create default category
        category = TokenCategory.objects.filter(
            facility=facility,
            resource_type=resource.resource_type,
        ).first()
        if not category:
            category = TokenCategory.objects.create(
                facility=facility,
                resource_type=resource.resource_type,
                name="General",
            )

        # Create token with lock
        with Lock(f"booking:token:{queue.id}"), transaction.atomic():
            number = Token.objects.filter(queue=queue, category=category).count() + 1
            token = Token.objects.create(
                facility=facility,
                queue=queue,
                category=category,
                number=number,
                status=TokenStatusOptions.CREATED.value,
                note=note,
                booking=booking,
                patient=booking.patient,
            )
            booking.token = token
            booking.status = BookingStatusChoices.booked.value
            booking.save(update_fields=["token", "status", "modified_date"])

        return self._build_response(booking, token)

    def _build_response(self, booking: TokenBooking, token: Token) -> dict:
        from ccm_uhi.mappers.catalog_mapper import map_facility_to_provider, map_slot_to_fulfillment
        from ccm_uhi.mappers.order_mapper import map_patient_to_billing

        result = {
            "booking_id": str(booking.external_id),
            "status": booking.status,
            "patient": map_patient_to_billing(booking.patient),
            "token":f"{token.category.shorthand} - {token.number}",
        }

        slot = booking.token_slot
        if slot:
            resource = slot.resource
            result["provider"] = map_facility_to_provider(resource.facility)
            result["fulfillment"] = map_slot_to_fulfillment(slot, resource)

        return result
