import json
import logging
import os
from typing import Any
from urllib import error, request
from uuid import uuid4

from django.conf import settings

from care.emr.models.patient import Patient, PatientIdentifier

logger = logging.getLogger(__name__)

DEFAULT_NOTIFICATION_ENDPOINT = "https://gateway-sandbox.curebay.in/command-center/push-notification/send"
ABHA_IDENTIFIER_SYSTEMS = (
    "system.care.ohc.network/patient-abha-address",
    "system.care.ohc.network/patient-abha-number",
)



def get_patient_abha_identifier(patient: Patient) -> str | None:
    """Resolve ABHA identifier value saved against a patient."""
    identifier = (
        PatientIdentifier.objects.filter(
            patient=patient,
            config__facility__isnull=True,
            config__config__system__in=ABHA_IDENTIFIER_SYSTEMS,
        )
        .select_related("config")
        .first()
    )
    if not identifier:
        return None
    value = (identifier.value or "").strip()
    return value or None


def send_patient_notification(*, fortype: str, patientid: str, notificationmessage: str) -> dict[str, Any]:
    """Fire-and-forget notification push to the CCM gateway endpoint."""
    endpoint = getattr(settings, "CCM_UHI_NOTIFICATION_ENDPOINT", DEFAULT_NOTIFICATION_ENDPOINT)
    enabled = getattr(settings, "CCM_UHI_NOTIFICATION_ENABLED", True)
    use_sms = getattr(settings, "CCM_UHI_NOTIFICATION_USE_SMS", False)

    payload = {
        "requestid": str(uuid4()).upper(),
        "fortype": fortype,
        "patientid": patientid,
        "notificationmessage": notificationmessage,
    }

    if not enabled:
        logger.info("Notification disabled, payload=%s", json.dumps(payload))
        return {"status": 200, "message": "Notification disabled", "payload": payload}

    if not use_sms:
        logger.info("USE_SMS disabled; notification skipped, payload=%s", json.dumps(payload))
        return {
            "status": 200,
            "message": "USE_SMS disabled; notification skipped",
            "payload": payload
        }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = getattr(settings, "CCM_UHI_NOTIFICATION_TIMEOUT", 5)

    try:
        with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            resp_body = resp.read().decode("utf-8") if resp else ""
            logger.info("Notification push success status=%s response=%s", getattr(resp, "status", 200), resp_body)
            return {
                "status": getattr(resp, "status", 200),
                "message": "Notification sent",
                "response": resp_body,
            }
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("Notification push failed status=%s error=%s", exc.code, detail)
        return {"status": exc.code, "message": detail}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Notification push failed due to unexpected error")
        return {"status": 500, "message": str(exc)}
