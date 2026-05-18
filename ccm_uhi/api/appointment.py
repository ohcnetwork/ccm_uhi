import logging

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from ccm_uhi.resources.common import RequestContext, build_response_context
from ccm_uhi.services.on_search_service import OnSearchService
from ccm_uhi.services.on_select_service import OnSelectService
from ccm_uhi.services.on_confirm_service import OnConfirmService
from ccm_uhi.services.on_status_service import OnStatusService
from ccm_uhi.services.on_cancel_service import OnCancelService
from ccm_uhi.services.on_reschedule_service import OnRescheduleService

logger = logging.getLogger(__name__)


def _parse_context(data: dict) -> dict:
    """Validate and extract the request context (message_id + timestamp)."""
    raw = data.get("context", {})
    ctx = RequestContext(**raw)
    return ctx.model_dump()


class AppointmentViewSet(ViewSet):
    authentication_classes = ()
    permission_classes = ()

    @action(detail=False, methods=["get"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def search(self, request, *args, **kwargs):
        provider_id = request.query_params.get("provider_id")
        try:
            result = OnSearchService().execute({}, {"provider_id": provider_id})
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)
        return Response(result, status=200)


    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def select(self, request, *args, **kwargs):
        try:
            req_context = _parse_context(request.data)
        except Exception as exc:
            return Response({"error": f"Invalid context: {exc}"}, status=400)

        message = request.data.get("message", {})
        provider_id = message.get("provider_id")
        doctor_id = message.get("doctor_id")
        department_id = message.get("department_id")

        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)
        if not doctor_id and not department_id:
            return Response({"error": "at least one of doctor_id or department_id is required"}, status=400)

        try:
            result = OnSelectService().execute({}, message)
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)

        facility = self._resolve_facility(provider_id)
        response_context = build_response_context(req_context, "select", facility)
        return Response({"context": response_context, "message": result}, status=200)

    # ── Init endpoint: COMMENTED OUT — merged into confirm ──────────
    #
    # @action(detail=False, methods=["post"])
    # @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    # def init(self, request, *args, **kwargs):
    #     message = request.data.get("message", {})
    #     provider_id = message.get("provider_id")
    #     item_id = message.get("item_id")
    #     fulfillment_id = message.get("fulfillment_id")
    #     patient = message.get("patient", {})
    #
    #     if not provider_id:
    #         return Response({"error": "provider_id is required"}, status=400)
    #     if not fulfillment_id:
    #         return Response({"error": "fulfillment_id is required"}, status=400)
    #     if not patient.get("name") or not patient.get("phone_number"):
    #         return Response({"error": "patient.name and patient.phone_number are required"}, status=400)
    #
    #     try:
    #         result = OnInitService().execute(
    #             {},
    #             {"order": {"provider_id": provider_id, "item_id": item_id, "fulfillment_id": fulfillment_id, "billing": patient}},
    #         )
    #     except (ValueError, Exception) as exc:
    #         return Response({"error": str(exc)}, status=422)
    #     return Response(result, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def confirm(self, request, *args, **kwargs):
        try:
            req_context = _parse_context(request.data)
        except Exception as exc:
            return Response({"error": f"Invalid context: {exc}"}, status=400)

        message = request.data.get("message", {})
        provider_id = message.get("provider_id")
        fulfillment_id = message.get("fulfillment_id")
        patient = message.get("patient", {})

        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)
        if not fulfillment_id:
            return Response({"error": "fulfillment_id is required"}, status=400)
        if not patient.get("name") or not patient.get("phone_number"):
            return Response(
                {"error": "patient.name and patient.phone_number are required"},
                status=400,
            )

        try:
            result = OnConfirmService().execute(
                {},
                {
                    "order": {
                        "provider_id": provider_id,
                        "fulfillment_id": fulfillment_id,
                        "billing": patient,
                        "note": message.get("note", ""),
                    }
                },
            )
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)

        facility = self._resolve_facility(provider_id)
        response_context = build_response_context(req_context, "confirm", facility)
        return Response({"context": response_context, "message": result}, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def status(self, request, *args, **kwargs):
        try:
            req_context = _parse_context(request.data)
        except Exception as exc:
            return Response({"error": f"Invalid context: {exc}"}, status=400)

        message = request.data.get("message", {})

        order_id = message.get("order_id")
        if not order_id:
            return Response({"error": "order_id is required"}, status=400)

        try:
            result = OnStatusService().execute({}, {"order_id": order_id})
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)

        facility = self._facility_from_booking(result)
        response_context = build_response_context(req_context, "status", facility)
        return Response({"context": response_context, "message": result}, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def cancel(self, request, *args, **kwargs):
        try:
            req_context = _parse_context(request.data)
        except Exception as exc:
            return Response({"error": f"Invalid context: {exc}"}, status=400)

        message = request.data.get("message", {})
        order_id = message.get("order_id")
        if not order_id:
            return Response({"error": "order_id is required"}, status=400)

        try:
            result = OnCancelService().execute({}, {"order_id": order_id})
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)

        facility = self._facility_from_booking(result)
        response_context = build_response_context(req_context, "cancel", facility)
        return Response({"context": response_context, "message": result}, status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(responses={200: dict}, tags=["CCM UHI"])
    def reschedule(self, request, *args, **kwargs):
        try:
            req_context = _parse_context(request.data)
        except Exception as exc:
            return Response({"error": f"Invalid context: {exc}"}, status=400)

        message = request.data.get("message", {})
        order_id = message.get("order_id")
        fulfillment_id = message.get("fulfillment_id")

        if not order_id:
            return Response({"error": "order_id is required"}, status=400)
        if not fulfillment_id:
            return Response({"error": "fulfillment_id is required"}, status=400)

        try:
            result = OnRescheduleService().execute(
                {},
                {
                    "order_id": order_id,
                    "fulfillment_id": fulfillment_id,
                    "note": message.get("note", ""),
                },
            )
        except (ValueError, Exception) as exc:
            return Response({"error": str(exc)}, status=422)

        facility = self._facility_from_booking(result)
        response_context = build_response_context(req_context, "reschedule", facility)
        return Response({"context": response_context, "message": result}, status=200)

    @staticmethod
    def _resolve_facility(provider_id):
        from care.facility.models.facility import Facility
        try:
            return Facility.objects.select_related("geo_organization").get(
                external_id=provider_id, is_active=True
            )
        except Facility.DoesNotExist:
            return None

    @staticmethod
    def _facility_from_booking(result: dict):
        """Extract facility from a booking-based service result for context building."""
        provider_id = (result.get("provider") or {}).get("id")
        if not provider_id:
            return None
        from care.facility.models.facility import Facility
        try:
            return Facility.objects.select_related("geo_organization").get(
                external_id=provider_id, is_active=True
            )
        except Facility.DoesNotExist:
            return None

