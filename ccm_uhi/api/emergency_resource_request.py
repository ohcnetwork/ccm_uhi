import logging
from typing import Optional
from uuid import UUID

from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field
from rest_framework.response import Response
from rest_framework.views import APIView

from ccm_uhi.services.emergency_resource_request_service import (
    EmergencyResourceRequestService,
)

logger = logging.getLogger(__name__)


class PatientSpec(BaseModel):
    name: str
    phone_number: str
    gender: str | None = None
    blood_group: str | None = None
    abha_number: str | None = None
    date_of_birth: str | None = None
    year_of_birth: int | None = None
    address: str | None = None
    permanent_address: str | None = None
    pincode: int | None = None

class AmbulanceSpec(BaseModel):
    vehicle_number: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    eta_minutes: int | None = None
    notes: str | None = None


class EmergencyResourceRequestSpec(BaseModel):
    provider_id: UUID
    patient: PatientSpec
    ambulance: AmbulanceSpec 
    title: str | None = None


class EmergencyResourceRequestView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        request=EmergencyResourceRequestSpec,
        responses={200: dict},
        tags=["CCM UHI"],
    )
    def post(self, request, *args, **kwargs):
        """Create an emergency resource request to alert a facility about an incoming ambulance."""
        try:
            spec = EmergencyResourceRequestSpec(**request.data)
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)

        try:
            result = EmergencyResourceRequestService().execute(spec.model_dump(exclude_none=True))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        except Exception as exc:
            logger.exception("Emergency resource request failed")
            return Response({"error": str(exc)}, status=400)

        return Response(result, status=200)
