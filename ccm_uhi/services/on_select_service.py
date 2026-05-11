"""
OnSelectService: Compute available slots for a specific doctor at a facility.

Takes provider_id (facility) + doctor_id (user external_id) + fulfillment
details (type, time window) and returns the slot catalog — the computation
that previously lived in OnSearchService.
"""

import datetime as dt
import logging
from datetime import timedelta

from django.utils import timezone

from care.emr.models.organization import FacilityOrganizationUser
from care.emr.models.scheduling.booking import TokenSlot
from care.emr.models.scheduling.schedule import (
    Availability,
    AvailabilityException,
    Schedule,
    SchedulableResource,
)
from care.emr.resources.scheduling.schedule.spec import SlotTypeOptions
from care.utils.time_util import care_now
from ccm_uhi.mappers.catalog_mapper import (
    build_catalog,
    resolve_facility,
)
from ccm_uhi.resources.common import FulfillmentType

logger = logging.getLogger(__name__)


class OnSelectService:
    """Compute and return available slots for a doctor at a facility."""

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

        # Compute available slots for each resource
        all_slots = []
        schedule_map = {}

        for resource in resources:
            slots, sched_map = self._compute_slots_for_resource(
                resource, time_start, time_end
            )
            all_slots.extend(slots)
            schedule_map.update(sched_map)

        if not all_slots:
            msg = "No available slots found for the requested time window"
            raise ValueError(msg)

        return build_catalog(
            facility=facility,
            slots=all_slots,
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
            msg = "Fulfillment start time must not be in the past"
            raise ValueError(msg)

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
        qs = SchedulableResource.objects.filter(
            deleted=False,
            facility=facility,
            resource_type="practitioner",
            user__isnull=False,
        ).select_related("user", "facility")

        if doctor_id:
            qs = qs.filter(user__external_id=doctor_id)

        if department_id:
            user_ids_in_dept = FacilityOrganizationUser.objects.filter(
                organization__facility=facility,
                organization__org_type="dept",
                organization__external_id=department_id,
                organization__active=True,
            ).values_list("user_id", flat=True)
            qs = qs.filter(user_id__in=user_ids_in_dept)

        return list(qs)

    def _compute_slots_for_resource(
        self,
        resource: SchedulableResource,
        time_start: dt.datetime,
        time_end: dt.datetime,
    ) -> tuple[list[TokenSlot], dict]:
        """
        Compute available slots for a resource across the date range.
        Generates TokenSlot records from Schedule+Availability config.
        """
        start_date = time_start.date()
        end_date = time_end.date()

        schedules = Schedule.objects.filter(
            resource=resource,
            valid_from__lte=end_date,
            valid_to__gte=start_date,
        ).select_related("charge_item_definition")

        if not schedules.exists():
            return [], {}

        availabilities = Availability.objects.filter(
            schedule__in=schedules,
            slot_type=SlotTypeOptions.appointment.value,
        ).select_related("schedule", "schedule__charge_item_definition")

        if not availabilities.exists():
            return [], {}

        exceptions = list(
            AvailabilityException.objects.filter(
                resource=resource,
                valid_from__lte=end_date,
                valid_to__gte=start_date,
            )
        )

        schedule_map = {a.id: (a.schedule, a) for a in availabilities}

        all_slots = []
        current_date = start_date
        now = care_now()

        while current_date <= end_date:
            day_slots = self._get_or_create_slots_for_day(
                resource, current_date, availabilities, exceptions, schedules, now
            )
            for slot in day_slots:
                if slot.start_datetime >= time_start and slot.end_datetime <= time_end:
                    tokens_per_slot = (
                        slot.availability.tokens_per_slot if slot.availability else None
                    )
                    if tokens_per_slot is None or slot.allocated < tokens_per_slot:
                        all_slots.append(slot)

            current_date += timedelta(days=1)

        return all_slots, schedule_map

    def _get_or_create_slots_for_day(
        self,
        resource: SchedulableResource,
        day: dt.date,
        availabilities,
        exceptions: list,
        schedules,
        now: dt.datetime,
    ) -> list[TokenSlot]:
        """Get existing TokenSlot records for the day, or create them from Availability config."""
        valid_schedule_ids = {
            s.id
            for s in schedules
            if timezone.make_naive(s.valid_from).date() <= day <= timezone.make_naive(s.valid_to).date()
        }

        day_availabilities = []
        for avail in availabilities:
            if avail.schedule_id not in valid_schedule_ids:
                continue
            for day_config in avail.availability:
                if day_config["day_of_week"] == day.weekday():
                    day_availabilities.append(
                        {
                            "availability": day_config,
                            "slot_size_in_minutes": avail.slot_size_in_minutes,
                            "availability_id": avail.id,
                        }
                    )

        if not day_availabilities:
            return []

        day_exceptions = [
            exc for exc in exceptions if exc.valid_from <= day <= exc.valid_to
        ]

        expected_slots = self._compute_day_slots(day, day_availabilities, day_exceptions)

        if not expected_slots:
            return []

        existing_slots = list(
            TokenSlot.objects.filter(
                start_datetime__date=day,
                end_datetime__date=day,
                resource=resource,
            ).select_related(
                "availability",
                "availability__schedule",
                "availability__schedule__charge_item_definition",
                "resource",
                "resource__user",
            )
        )

        existing_keys = {
            f"{timezone.make_naive(s.start_datetime).time()}-{timezone.make_naive(s.end_datetime).time()}-{s.availability_id}"
            for s in existing_slots
        }

        new_slots = []
        for slot_info in expected_slots:
            key = f"{slot_info['start_time']}-{slot_info['end_time']}-{slot_info['availability_id']}"
            if key in existing_keys:
                continue

            end_datetime = dt.datetime.combine(day, slot_info["end_time"])
            if end_datetime < timezone.make_naive(now):
                continue

            new_slot = TokenSlot.objects.create(
                resource=resource,
                start_datetime=dt.datetime.combine(day, slot_info["start_time"]),
                end_datetime=end_datetime,
                availability_id=slot_info["availability_id"],
            )
            new_slots.append(new_slot)

        if new_slots:
            existing_slots = list(
                TokenSlot.objects.filter(
                    start_datetime__date=day,
                    end_datetime__date=day,
                    resource=resource,
                ).select_related(
                    "availability",
                    "availability__schedule",
                    "availability__schedule__charge_item_definition",
                    "resource",
                    "resource__user",
                )
            )

        return existing_slots

    @staticmethod
    def _compute_day_slots(
        day: dt.date,
        availabilities: list[dict],
        exceptions: list,
    ) -> list[dict]:
        """Compute slot time ranges for a day from availability config, excluding exceptions."""
        slots = []
        for availability in availabilities:
            start_time = dt.datetime.combine(
                day,
                dt.time.fromisoformat(availability["availability"]["start_time"]),
            )
            end_time = dt.datetime.combine(
                day,
                dt.time.fromisoformat(availability["availability"]["end_time"]),
            )
            slot_size = availability["slot_size_in_minutes"]
            availability_id = availability["availability_id"]

            current = start_time
            while current < end_time:
                slot_end = current + timedelta(minutes=slot_size)

                conflicting = False
                for exc in exceptions:
                    exc_start = dt.datetime.combine(day, exc.start_time)
                    exc_end = dt.datetime.combine(day, exc.end_time)
                    if exc_start < slot_end and exc_end > current:
                        conflicting = True
                        break

                if not conflicting:
                    slots.append(
                        {
                            "start_time": current.time(),
                            "end_time": slot_end.time(),
                            "availability_id": availability_id,
                        }
                    )

                current = slot_end

        return slots
