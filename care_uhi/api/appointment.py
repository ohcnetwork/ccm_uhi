import logging

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from care_uhi.models import BecknOrder
from care_uhi.resources.cancel.spec import CancelRequest
from care_uhi.resources.confirm.spec import ConfirmRequest
from care_uhi.resources.init.spec import InitRequest
from care_uhi.resources.search.spec import SearchRequest
from care_uhi.resources.select.spec import SelectRequest
from care_uhi.resources.status.spec import StatusRequest
from care_uhi.tasks.beckn_tasks import process_beckn_request
from care_uhi.utils.helpers import TransactionClosedError, update_or_create_transaction
from care_uhi.utils.response import build_ack, build_nack, format_validation_errors

logger = logging.getLogger(__name__)


class AppointmentViewSet(ViewSet):
    authentication_classes = ()
    permission_classes = ()

    @action(detail=False, methods=["post"])
    @extend_schema(request=SearchRequest, responses={200: dict},tags=["UHI - HSPA"])
    def search(self, request, *args, **kwargs):
        try:
            SearchRequest(**request.data)
        except Exception as exc:
            return Response(build_nack(format_validation_errors(exc)), status=400)

        context = request.data["context"]
        try:
            update_or_create_transaction(context, "search", request.data)
        except TransactionClosedError as exc:
            return Response(build_nack(str(exc)), status=400)
        process_beckn_request.delay(str(context["message_id"]))
        return Response(build_ack(), status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(request=SelectRequest, responses={200: dict},tags=["UHI - HSPA"])
    def select(self, request, *args, **kwargs):
        try:
            SelectRequest(**request.data)
        except Exception as exc:
            return Response(build_nack(format_validation_errors(exc)), status=400)

        context = request.data["context"]
        try:
            update_or_create_transaction(context, "select", request.data)
        except TransactionClosedError as exc:
            return Response(build_nack(str(exc)), status=422)
        process_beckn_request.delay(str(context["message_id"]))
        return Response(build_ack(), status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(request=InitRequest, responses={200: dict},tags=["UHI - HSPA"])
    def init(self, request, *args, **kwargs):
        try:
            InitRequest(**request.data)
        except Exception as exc:
            return Response(build_nack(format_validation_errors(exc)), status=400)

        context = request.data["context"]
        try:
            update_or_create_transaction(context, "init", request.data)
        except TransactionClosedError as exc:
            return Response(build_nack(str(exc)), status=422)
        process_beckn_request.delay(str(context["message_id"]))
        return Response(build_ack(), status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(request=ConfirmRequest, responses={200: dict},tags=["UHI - HSPA"])
    def confirm(self, request, *args, **kwargs):
        try:
            ConfirmRequest(**request.data)
        except Exception as exc:
            return Response(build_nack(format_validation_errors(exc)), status=400)

        context = request.data["context"]
        message = request.data.get("message", {})
        order_id = message.get("order_id", "")
        if not order_id or not BecknOrder.objects.filter(
            order_id=order_id, transaction_id=context["transaction_id"]
        ).exists():
            return Response(
                build_nack(f"Order {order_id} not found for this transaction"), status=422
            )

        try:
            update_or_create_transaction(context, "confirm", request.data)
        except TransactionClosedError as exc:
            return Response(build_nack(str(exc)), status=422)
        process_beckn_request.delay(str(context["message_id"]))
        return Response(build_ack(), status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(request=StatusRequest, responses={200: dict},tags=["UHI - HSPA"])
    def status(self, request, *args, **kwargs):
        try:
            StatusRequest(**request.data)
        except Exception as exc:
            return Response(build_nack(format_validation_errors(exc)), status=400)

        context = request.data["context"]
        message = request.data.get("message", {})
        order_id = message.get("order_id", "") or message.get("order", {}).get("id", "")
        if not order_id or not BecknOrder.objects.filter(
            order_id=order_id, transaction_id=context["transaction_id"]
        ).exists():
            return Response(
                build_nack(f"Order {order_id} not found for this transaction"), status=422
            )

        try:
            update_or_create_transaction(context, "status", request.data)
        except TransactionClosedError as exc:
            return Response(build_nack(str(exc)), status=422)
        process_beckn_request.delay(str(context["message_id"]))
        return Response(build_ack(), status=200)

    @action(detail=False, methods=["post"])
    @extend_schema(request=CancelRequest, responses={200: dict},tags=["UHI - HSPA"])
    def cancel(self, request, *args, **kwargs):
        try:
            CancelRequest(**request.data)
        except Exception as exc:
            return Response(build_nack(format_validation_errors(exc)), status=400)

        context = request.data["context"]
        message = request.data.get("message", {})
        order_id = message.get("order_id", "")
        if not order_id or not BecknOrder.objects.filter(
            order_id=order_id, transaction_id=context["transaction_id"]
        ).exists():
            return Response(
                build_nack(f"Order {order_id} not found for this transaction"), status=422
            )

        try:
            update_or_create_transaction(context, "cancel", request.data)
        except TransactionClosedError as exc:
            return Response(build_nack(str(exc)), status=422)
        process_beckn_request.delay(str(context["message_id"]))
        return Response(build_ack(), status=200)
