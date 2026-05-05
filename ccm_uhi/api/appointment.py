import logging

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from ccm_uhi.services.on_search_service import OnSearchService
from ccm_uhi.services.on_select_service import OnSelectService
from ccm_uhi.services.on_init_service import OnInitService
from ccm_uhi.services.on_confirm_service import OnConfirmService
from ccm_uhi.services.on_status_service import OnStatusService
from ccm_uhi.services.on_cancel_service import OnCancelService

logger = logging.getLogger(__name__)


class AppointmentViewSet(ViewSet):
    authentication_classes = ()
    permission_classes = ()

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def search(self, request, *args, **kwargs):
        message = request.data.get("message", {})
        provider_id = message.get("provider_id")
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)
        try:
            result = OnSearchService().execute({}, message)
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)
        return Response(result, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def select(self, request, *args, **kwargs):

        message = request.data.get("message", {})
        provider_id = message.get("provider_id")
        item_id = message.get("item_id")
        fulfillment_id = message.get("fulfillment_id")

        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)
        if not item_id:
            return Response({"error": "item_id is required"}, status=400)
        if not fulfillment_id:
            return Response({"error": "fulfillment_id is required"}, status=400)

        message = {"order": {"provider_id": provider_id, "item_id": item_id, "fulfillment_id": fulfillment_id}}
        try:
            result = OnSelectService().execute({}, message)
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)
        return Response(result, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def init(self, request, *args, **kwargs):
        message = request.data.get("message", {})
        provider_id = message.get("provider_id")
        item_id = message.get("item_id")
        fulfillment_id = message.get("fulfillment_id")
        patient = message.get("patient", {})

        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)
        if not fulfillment_id:
            return Response({"error": "fulfillment_id is required"}, status=400)
        if not patient.get("name") or not patient.get("phone_number"):
            return Response({"error": "patient.name and patient.phone_number are required"}, status=400)

        try:
            result = OnInitService().execute(
                {},
                {"order": {"provider_id": provider_id, "item_id": item_id, "fulfillment_id": fulfillment_id, "billing": patient}},
            )
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)
        return Response(result, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def confirm(self, request, *args, **kwargs):
        """
        Confirm a booking.
        Body: { "booking_id": "<uuid>" }
        """
        message = request.data.get("message", {})
        booking_id = message.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=400)

        try:
            result = OnConfirmService().execute({}, {"booking_id": booking_id})
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)
        return Response(result, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def status(self, request, *args, **kwargs):
        """
        Get booking status.
        Body: { "booking_id": "<uuid>" }
        """
        message = request.data.get("message", {})

        booking_id = message.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=400)

        try:
            result = OnStatusService().execute({}, {"booking_id": booking_id})
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)
        return Response(result, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def cancel(self, request, *args, **kwargs):
        """
        Cancel a booking.
        Body: { "booking_id": "<uuid>" }
        """
        message = request.data.get("message", {})
        booking_id = message.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=400)

        try:
            result = OnCancelService().execute({}, {"booking_id": booking_id})
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)
        return Response(result, status=200)
