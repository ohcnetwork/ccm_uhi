"""
OnSelectService: Return available slots for a doctor/department at a facility.

Takes provider_id (facility) + doctor_id and/or department_id + optional
time window and returns existing available TokenSlots as a Beckn catalog.
"""

import datetime as dt
import logging
from datetime import timedelta

from django.utils import timezone

from care.emr.api.viewsets.scheduling.availability import SlotViewSet
from care.emr.models.organization import FacilityOrganizationUser
from care.emr.models.scheduling.booking import TokenSlot
from care.emr.models.scheduling.schedule import SchedulableResource
from care.utils.time_util import care_now
from ccm_uhi.mappers.catalog_mapper import (
    build_catalog,
    resolve_facility,
)
from ccm_uhi.resources.common import FulfillmentType

logger = logging.getLogger(__name__)


class OnSelectService:
    """Return available slots for a doctor at a facility."""

    def execute(self, context: dict, message: dict) -> dict:
        provider_id = message.get("provider_id")
        doctor_id = message.get("doctor_id")
        department_id = message.get("department_id")

        if not provider_id:
            msg = "provider_id is required"
            raise ValueError(msg)
        if not doctor_id and not department_id:
            msg = "at least one of doctor_id or department_id is required"
            raise ValueError(msg)

        facility = resolve_facility(provider_id)

        fulfillment_type = self._get_fulfillment_type(message)
        time_start, time_end = self._get_time_window(message)

        # Find the specific doctor's schedulable resource
        resources = self._find_resources(facility, doctor_id, department_id)
        if not resources:
            msg = "No schedulable resource found for the given doctor"
            raise ValueError(msg)

        resource_map = {r.id: r for r in resources}

        start_date = time_start.date()
        end_date = time_end.date()
        current_date = start_date

        while current_date <= end_date:
            for resource in resources:
                SlotViewSet.get_slots_for_day_handler(
                    str(facility.external_id),
                    {
                        "resource_type": resource.resource_type,
                        "resource_id": str(resource.user.external_id),
                        "day": current_date.isoformat(),
                    },
                )
            current_date += timedelta(days=1)

        # Now fetch all slots in the time window
        slots = list(
            TokenSlot.objects.filter(
                resource__in=resources,
                end_datetime__gt=time_start,
                start_datetime__lte=time_end,
                deleted=False,
            ).select_related(
                "availability",
                "availability__schedule",
                "availability__schedule__charge_item_definition",
                "resource",
                "resource__user",
            )
        )

        # Filter to slots with remaining capacity
        available_slots = []
        for slot in slots:
            tokens_per_slot = (
                slot.availability.tokens_per_slot if slot.availability else None
            )
            if tokens_per_slot is None or slot.allocated < tokens_per_slot:
                available_slots.append(slot)

        if not available_slots:
           return build_catalog(
                facility=facility,
                slots=[],
                resource_map={},
                schedule_map={},
                fulfillment_type=fulfillment_type,
            )

        # Build schedule_map from the slots' availability records
        schedule_map = {}
        for slot in available_slots:
            if slot.availability_id and slot.availability_id not in schedule_map:
                schedule_map[slot.availability_id] = (
                    slot.availability.schedule,
                    slot.availability,
                )

        return build_catalog(
            facility=facility,
            slots=available_slots,
            resource_map=resource_map,
            schedule_map=schedule_map,
            fulfillment_type=fulfillment_type,
        )

    def _get_fulfillment_type(self, message: dict) -> str:
        fulfillment = message.get("fulfillment", {})
        return fulfillment.get("type", FulfillmentType.physical.value)

    def _get_time_window(self, message: dict) -> tuple[dt.datetime, dt.datetime]:
        fulfillment = message.get("fulfillment", {})
        start_ts = fulfillment.get("start", {}).get("time", {}).get("timestamp")
        end_ts = fulfillment.get("end", {}).get("time", {}).get("timestamp")

        now = care_now()

        time_start = self._parse_aware(start_ts) if start_ts else now
        time_end = self._parse_aware(end_ts) if end_ts else now + timedelta(days=7)

        if time_start < now:
            time_start = now

        if time_end <= time_start:
            msg = "Fulfillment end time must be after start time"
            raise ValueError(msg)

        return time_start, time_end

    @staticmethod
    def _parse_aware(iso_string: str) -> dt.datetime:
        parsed = dt.datetime.fromisoformat(iso_string)
        if not timezone.is_aware(parsed):
            parsed = timezone.make_aware(parsed)
        return parsed

    def _find_resources(self, facility, doctor_id: str | None = None, department_id: str | None = None) -> list[SchedulableResource]:
        filters = {"deleted": False, "facility": facility, "resource_type": "practitioner", "user__isnull": False}
        if doctor_id:
            filters["user__external_id"] = doctor_id

        if department_id:
            user_ids_in_dept = FacilityOrganizationUser.objects.filter(
                organization__facility=facility,
                organization__org_type="dept",
                organization__external_id=department_id,
                organization__active=True,
            ).values_list("user_id", flat=True)
            filters["user_id__in"] = user_ids_in_dept

        qs = SchedulableResource.objects.filter(**filters).select_related("user", "facility")



        return list(qs)


