"""
OnInitService: Handles Beckn /on_init callback.

Validates slot availability, creates a draft TokenBooking in CARE,
and returns a Beckn order with quote and terms.
"""

import logging

from django.db import transaction

from care.emr.api.viewsets.scheduling import lock_create_appointment
from care.emr.models.patient import Patient
from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.resources.patient.spec import PatientCreateSpec
from care.facility.models.facility import Facility
from ccm_uhi.mappers.order_mapper import build_terms, map_booking_to_order
from ccm_uhi.models import BecknOrder
from ccm_uhi.resources.common import OrderState


logger = logging.getLogger(__name__)


class SlotUnavailableError(Exception):
    pass


class PatientNotRegisteredError(Exception):
    pass


class OnInitService:
    """Process a Beckn init request: validate + create draft booking."""

    def execute(self, context: dict, message: dict) -> dict:
        order_msg = message.get("order", {})

        provider_id = order_msg.get("provider_id")
        item_id = order_msg.get("item_id")
        fulfillment_id = order_msg.get("fulfillment_id")
        billing = order_msg.get("billing", {})

        if not provider_id:
            msg = "Provider provider_id is required"
            raise ValueError(msg)
        if not item_id:
            msg = "Item ID is required"
            raise ValueError(msg)
        if not fulfillment_id:
            msg = "Fulfillment ID is required"
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

        # Create Beckn order record
        with transaction.atomic():
            beckn_order = self._create_beckn_order(
                booking=booking,
                transaction_id=context.get("transaction_id", ""),
                consumer_id=context.get("consumer_id", ""),
                consumer_uri=context.get("consumer_uri", ""),
                provider_id=provider_id,
                item_id=item_id,
                fulfillment_id=fulfillment_id,
                billing=billing,
                status=OrderState.initialized.value,
            )

        return map_booking_to_order(beckn_order)

    def _resolve_slot(self, fulfillment_id: str) -> TokenSlot:
        try:
            return TokenSlot.objects.select_related(
                "resource", "resource__user", "resource__facility", "availability"
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
            msg = "billing.phone_number is required"
            raise PatientNotRegisteredError(msg)

        if not name:
            msg = "billing.name is required"
            raise PatientNotRegisteredError(msg)

        patient = Patient.objects.filter(
            phone_number=phone, name__icontains=name, deleted=False
        ).first()
        if patient:
            return patient

        # Validate and create using PatientCreateSpec
        spec = PatientCreateSpec(**billing)
        patient = spec.de_serialize()
        patient.save()
        return patient



    def _create_beckn_order(
        self,
        booking: TokenBooking,
        transaction_id: str,
        consumer_id: str,
        consumer_uri: str,
        provider_id: str,
        item_id: str,
        fulfillment_id: str,
        billing: dict,
        status: str,
    ) -> BecknOrder:
        return BecknOrder.objects.create(
            transaction_id=transaction_id,
            booking=booking,
            status=status,
            consumer_id=consumer_id,
            consumer_uri=consumer_uri,
            provider_id=provider_id,
            item_id=item_id,
            fulfillment_id=fulfillment_id,
            billing=billing,
            terms=build_terms(),
        )
