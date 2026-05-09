
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from care.emr.api.viewsets.scheduling import lock_create_appointment
from care.emr.models.organization import Organization
from care.emr.models.patient import Patient
from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.resources.patient.spec import PatientCreateSpec
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices
from care.emr.resources.scheduling.token.spec import TokenStatusOptions
from care.emr.models.scheduling.token import Token, TokenCategory, TokenQueue
from care.facility.models.facility import Facility
from care.utils.lock import Lock

logger = logging.getLogger(__name__)


class SlotUnavailableError(Exception):
    pass


class PatientNotRegisteredError(Exception):
    pass


class OnConfirmService:
    """Create a booking and confirm it with a token in a single call."""

    def execute(self, context: dict, message: dict) -> dict:
        order_msg = message.get("order", {})

        provider_id = order_msg.get("provider_id")
        fulfillment_id = order_msg.get("fulfillment_id")
        billing = order_msg.get("billing", {})
        note = order_msg.get("note", "")

        if not provider_id:
            msg = "provider_id is required"
            raise ValueError(msg)
        if not fulfillment_id:
            msg = "fulfillment_id is required"
            raise ValueError(msg)

        # --- Step 1: Resolve slot, facility, patient (from init) ---
        slot = self._resolve_slot(fulfillment_id)
        facility = self._resolve_facility(provider_id)
        patient = self._resolve_or_create_patient(billing)

        if slot.resource.facility_id != facility.id:
            msg = "Slot does not belong to the requested provider"
            raise ValueError(msg)

        # --- Step 2: Create draft booking (from init) ---
        booking = lock_create_appointment(slot, patient, created_by=None, note=note)

        # --- Steps 3-4: Create token and update status (from confirm) ---
        token = self._create_token_and_confirm(booking, note)

        # --- Step 5: Build combined response ---
        return self._build_response(booking, facility, slot, token)

    # ── Init-originated helpers ──────────────────────────────────────

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
            raise SlotUnavailableError(msg)

    def _resolve_facility(self, descriptor_id: str) -> Facility:
        try:
            return Facility.objects.get(external_id=descriptor_id)
        except Facility.DoesNotExist:
            msg = f"Provider {descriptor_id} not found"
            raise ValueError(msg)

    def _resolve_or_create_patient(self, billing: dict) -> Patient:
        """Find existing patient by phone and name, or create via PatientCreateSpec."""
        phone = billing.get("phone_number", "")
        name = billing.get("name", "")

        if not phone:
            msg = "patient.phone_number is required"
            raise PatientNotRegisteredError(msg)

        if not name:
            msg = "patient.name is required"
            raise PatientNotRegisteredError(msg)

        patient = Patient.objects.filter(
            phone_number=phone, name__icontains=name, deleted=False
        ).first()
        if patient:
            return patient

        billing["geo_organization"] = str(
            Organization.objects.filter(org_type="govt").first().external_id
        )
        spec = PatientCreateSpec(**billing)
        patient = spec.de_serialize()
        patient.save()
        return patient

    # ── Confirm-originated helpers ───────────────────────────────────

    def _create_token_and_confirm(self, booking: TokenBooking, note: str) -> Token:
        """Create token queue/category/token and mark booking as booked."""
        if booking.status in (
            BookingStatusChoices.cancelled.value,
            BookingStatusChoices.fulfilled.value,
        ):
            msg = f"Booking is already '{booking.status}' and cannot be confirmed"
            raise ValueError(msg)

        if booking.token:
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
            create_filters = {
                **filters,
                "name": "System Generated",
                "system_generated": True,
            }
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

        return token

    # ── Response builder ─────────────────────────────────────────────

    def _build_response(
        self, booking: TokenBooking, facility: Facility, slot: TokenSlot, token: Token
    ) -> dict:
        from ccm_uhi.mappers.catalog_mapper import (
            extract_price,
            map_facility_to_provider,
            map_schedule_to_item,
            map_slot_to_fulfillment,
        )
        from ccm_uhi.mappers.order_mapper import map_patient_to_billing

        resource = slot.resource
        availability = slot.availability
        schedule = availability.schedule if availability else None

        result = {
            "order_id": str(booking.external_id),
            "status": booking.status,
            "provider": map_facility_to_provider(facility),
            "patient": map_patient_to_billing(booking.patient),
            "fulfillment": map_slot_to_fulfillment(slot, resource),
            "token": f"{token.category.shorthand} - {token.number}",
        }

        if schedule:
            result["item"] = map_schedule_to_item(
                schedule, availability, str(slot.external_id)
            )
            price_info = extract_price(schedule)
            result["quote"] = {
                "price": {
                    "currency": price_info["currency"],
                    "value": price_info["value"],
                },
                "breakup": price_info.get("breakup", []),
            }

        return result
