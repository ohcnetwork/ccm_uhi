"""
OnInitService: Create a draft booking.

Validates slot availability, creates a draft TokenBooking in CARE,
and returns booking details with quote.
"""

import logging
from care.emr.models.organization import Organization
from care.emr.api.viewsets.scheduling import lock_create_appointment
from care.emr.models.patient import Patient
from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.resources.patient.spec import PatientCreateSpec
from care.facility.models.facility import Facility
from ccm_uhi.mappers.catalog_mapper import (
    extract_price,
    map_facility_to_provider,
    map_schedule_to_item,
    map_slot_to_fulfillment,
    resolve_facility,
)
from ccm_uhi.mappers.order_mapper import map_patient_to_billing


logger = logging.getLogger(__name__)


class SlotUnavailableError(Exception):
    pass


class PatientNotRegisteredError(Exception):
    pass


class OnInitService:
    """Process an init request: validate + create draft booking."""

    def execute(self, context: dict, message: dict) -> dict:
        order_msg = message.get("order", {})

        provider_id = order_msg.get("provider_id")
        item_id = order_msg.get("item_id")
        fulfillment_id = order_msg.get("fulfillment_id")
        billing = order_msg.get("billing", {})

        if not provider_id:
            msg = "facility_id (provider_id) is required"
            raise ValueError(msg)
        if not fulfillment_id:
            msg = "fulfillment_id is required"
            raise ValueError(msg)

        # Resolve CARE objects
        slot = self._resolve_slot(fulfillment_id)
        patient = self._resolve_or_create_patient(billing)
        facility = self._resolve_facility(provider_id)

        # Validate slot belongs to the requested facility
        if slot.resource.facility_id != facility.id:
            msg = "Slot does not belong to the requested provider"
            raise ValueError(msg)

        # Create booking using CARE's lock handler (validates capacity + duplicates)
        booking = lock_create_appointment(slot, patient, created_by=None, note="")

        # Build response from booking
        return self._build_response(booking, facility, slot)

    def _build_response(self, booking: TokenBooking, facility, slot: TokenSlot) -> dict:
        resource = slot.resource
        availability = slot.availability
        schedule = availability.schedule if availability else None

        result = {
            "booking_id": str(booking.external_id),
            "status": booking.status,
            "provider": map_facility_to_provider(facility),
            "patient": map_patient_to_billing(booking.patient),
            "fulfillment": map_slot_to_fulfillment(slot, resource),
        }

        if schedule:
            result["item"] = map_schedule_to_item(schedule, availability, str(slot.external_id))
            price_info = extract_price(schedule)
            result["quote"] = {
                "price": {"currency": price_info["currency"], "value": price_info["value"]},
                "breakup": price_info.get("breakup", []),
            }

        return result

    def _resolve_slot(self, fulfillment_id: str) -> TokenSlot:
        try:
            return TokenSlot.objects.select_related(
                "resource", "resource__user", "resource__facility", "availability",
                "availability__schedule", "availability__schedule__charge_item_definition",
            ).get(external_id=fulfillment_id, deleted=False)
        except TokenSlot.DoesNotExist:
            msg = f"Slot {fulfillment_id} not found"
            raise SlotUnavailableError(msg)

    def _resolve_facility(self, descriptor_id: str) -> Facility:
        return Facility.objects.get(external_id=descriptor_id)

    def _resolve_or_create_patient(self, billing: dict) -> Patient:
        """Find existing patient by phone and name, or create using PatientCreateSpec."""
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

        # Validate and create using PatientCreateSpec
        billing["geo_organization"] = str(Organization.objects.filter(org_type="govt").first().external_id)
        spec = PatientCreateSpec(**billing)
        patient = spec.de_serialize()
        patient.save()
        return patient
