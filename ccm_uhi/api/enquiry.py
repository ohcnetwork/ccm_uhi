from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from ccm_uhi.services.service_availability_service import ServiceAvailabilityService


class ServiceAvailabilityView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def post(self, request, *args, **kwargs):
        """List healthcare services at a facility with optional filters."""

        provider_id = request.data.get("provider_id")
        pincode = request.data.get("pincode")
        service_names = request.data.get("services")
        pincode_int = None
        if pincode:
            try:
                pincode_int = int(pincode)
            except (ValueError, TypeError):
                return Response({"error": "pincode must be a valid integer"}, status=400)

        try:
            result = ServiceAvailabilityService().execute(
                facility_external_id=provider_id,
                facility_pincode=pincode_int,
                service_names=service_names,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=422)

        return Response(result, status=200)
