import logging

from django.db import transaction

from care.emr.models.patient import Patient
from care.emr.models.resource_request import ResourceRequest
from care.facility.models.facility import Facility

from ccm_uhi.services.on_confirm_service import OnConfirmService

logger = logging.getLogger(__name__)


class EmergencyResourceRequestService:
    """Create a resource request for an incoming emergency ambulance."""

    DEFAULT_TITLE = "Emergency Admission"
    DEFAULT_CATEGORY = "patient_care"
    DEFAULT_STATUS = "transfer_in_progress"

    def execute(self, data: dict) -> dict:
        facility_id = data.get("provider_id")
        patient_data = data.get("patient", {})
        ambulance_data = data.get("ambulance", {})
        title = data.get("title") or self.DEFAULT_TITLE

        with transaction.atomic():
            facility = self._resolve_facility(facility_id)
            patient = self._resolve_or_create_patient(patient_data)

            existing = ResourceRequest.objects.filter(
                related_patient=patient,
                status__in=("pending", "transfer_in_progress"),
            ).exists()
            if existing:
                raise ValueError("An active emergency request already exists for this patient")

            resource_request = self._create_resource_request(
                facility=facility,
                patient=patient,
                title=title,
                ambulance_data=ambulance_data,
            )

        return self._build_response(resource_request, facility, patient, ambulance_data)

    def _resolve_facility(self, facility_id: str) -> Facility:
        try:
            return Facility.objects.get(external_id=facility_id, is_active=True)
        except Facility.DoesNotExist:
            raise ValueError(f"Facility {facility_id} not found")

    def _resolve_or_create_patient(self, patient_data: dict) -> Patient:
        return OnConfirmService()._resolve_or_create_patient(patient_data)

    def _create_resource_request(
        self,
        facility: Facility,
        patient: Patient,
        title: str,
        ambulance_data: dict,
    ) -> ResourceRequest:
        reason_parts = ["Emergency ambulance incoming."]

        if ambulance_data.get("vehicle_number"):
            reason_parts.append(f"Vehicle: {ambulance_data['vehicle_number']}")
        if ambulance_data.get("driver_name"):
            reason_parts.append(f"Driver: {ambulance_data['driver_name']}")
        if ambulance_data.get("driver_phone"):
            reason_parts.append(f"Driver Phone: {ambulance_data['driver_phone']}")
        if ambulance_data.get("eta_minutes"):
            reason_parts.append(f"ETA: {ambulance_data['eta_minutes']} minutes")
        if ambulance_data.get("notes"):
            reason_parts.append(f"Notes: {ambulance_data['notes']}")

        reason = "\n".join(reason_parts)

        resource_request = ResourceRequest(
            origin_facility=facility,
            assigned_facility=facility,
            emergency=True,
            title=title,
            reason=reason,
            referring_facility_contact_name=patient.name,
            referring_facility_contact_number=patient.phone_number or "",
            status=self.DEFAULT_STATUS,
            category=self.DEFAULT_CATEGORY,
            priority=1,
            related_patient=patient,
        )
        resource_request.save()
        return resource_request

    def _build_response(
        self,
        resource_request: ResourceRequest,
        facility: Facility,
        patient: Patient,
        ambulance_data: dict,
    ) -> dict:
        return {
            "resource_request": {
                "id": str(resource_request.external_id),
                "title": resource_request.title,
                "status": resource_request.status,
                "emergency": resource_request.emergency,
                "reason": resource_request.reason,
                "category": resource_request.category,
                "priority": resource_request.priority,
            },
            "facility": {
                "id": str(facility.external_id),
                "name": facility.name,
            },
            "patient": {
                "id": str(patient.external_id),
                "name": patient.name,
                "phone_number": patient.phone_number,
            },
            "ambulance": ambulance_data,
        }
