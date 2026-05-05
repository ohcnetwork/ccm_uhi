
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ccm_uhi.constants import CARE_CATALOG_DESCRIPTOR
from ccm_uhi.resources.common import FulfillmentType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from care.emr.models.scheduling.booking import TokenSlot
    from care.emr.models.scheduling.schedule import (
        Availability,
        Schedule,
        SchedulableResource,
    )
    from care.users.models import User

from care.facility.models.facility import Facility


def resolve_facility(external_id: str) -> Facility:
    """Look up an active facility by external_id. Raises ValueError if not found."""
    try:
        return Facility.objects.get(external_id=external_id, is_active=True)
    except Facility.DoesNotExist:
        msg = f"Provider {external_id} not found"
        raise ValueError(msg)


def map_facility_to_provider(facility: Facility) -> dict:
    """Facility → Beckn provider block (one per hospital/facility)."""
    return {
        "id": str(facility.external_id),
        "descriptor": {
            "name": facility.name,
            "short_desc": facility.description or "",
        },
        "location": {
            "id": str(facility.external_id),
            "gps": (
                f"{facility.latitude},{facility.longitude}"
                if facility.latitude and facility.longitude
                else ""
            ),
            "address": facility.address or "",
        },
    }


def map_user_to_agent(user: User) -> dict:
    """Practitioner (SchedulableResource.user) → Beckn fulfillment.agent."""
    name_parts = [user.prefix or "", user.first_name, user.last_name, user.suffix or ""]
    full_name = " ".join(p for p in name_parts if p).strip()

    return {
        "id": str(user.external_id),
        "name": full_name or user.username,
        "gender": user.gender or "",
        "tags": [
            {
                "descriptor": {"code": "qualification"},
                "list": [{"value": user.qualification or ""}],
            },
            {
                "descriptor": {"code": "experience"},
                "list": [
                    {"value": str(user.doctor_experience_commenced_on or "")}
                ],
            },
        ],
    }


def map_slot_to_fulfillment(
    slot: TokenSlot,
    resource: SchedulableResource,
    fulfillment_type: str = "physical",
) -> dict:
    """TokenSlot + SchedulableResource → Beckn fulfillment."""
    agent = {}
    if resource.user:
        agent = map_user_to_agent(resource.user)

    return {
        "id": str(slot.external_id),
        "type": fulfillment_type,
        "agent": agent,
        "start": {
            "time": {
                "timestamp": slot.start_datetime.isoformat(),
            },
        },
        "end": {
            "time": {
                "timestamp": slot.end_datetime.isoformat(),
            },
        },
    }


def extract_price(schedule: Schedule) -> dict:
    """Extract price from Schedule's ChargeItemDefinition price_components.

    Handles two kinds of components:
      - Direct amount
      - Factor (percentage of base)

    Returns a Beckn price object with:
      - value: computed total (base - discounts + taxes)
      - breakup: individual component amounts with labels
    """
    if not schedule.charge_item_definition:
        return {"currency": "INR", "value": "0", "breakup": []}

    cid = schedule.charge_item_definition
    price_components = cid.price_components or []

    # First pass: find the base amount
    base_amount = 0.0
    for pc in price_components:
        if not isinstance(pc, dict):
            continue
        if pc.get("monetary_component_type") == "base":
            base_amount = float(pc.get("amount", 0) or 0)
            break

    # Second pass: compute each component's resolved amount
    breakup = []
    total = 0.0
    for pc in price_components:
        if not isinstance(pc, dict):
            continue

        comp_type = pc.get("monetary_component_type", "base")
        amount = pc.get("amount")
        factor = pc.get("factor")

        # Resolve the effective amount for this component
        if amount is not None:
            resolved = float(amount)
        elif factor is not None:
            resolved = round(base_amount * float(factor) / 100, 2)
        else:
            resolved = 0.0

        # Label from code.display or fall back to component type
        code = pc.get("code")
        label = code.get("display") if isinstance(code, dict) else None
        label = label or comp_type

        breakup.append(
            {
                "title": label,
                "price": {
                    "currency": "INR",
                    "value": str(resolved),
                },
            }
        )

        # Accumulate total: base and surcharge/tax add, discount subtracts
        if comp_type == "discount":
            total -= resolved
        else:
            total += resolved

    return {
        "currency": "INR",
        "value": str(round(total, 2)),
        "breakup": breakup,
    }


def map_schedule_to_item(
    schedule: Schedule,
    availability: Availability,
    fulfillment_id: str,
) -> dict:
    """Schedule + Availability + slot → Beckn item (bookable service).

    1:1 with fulfillment — each slot gets its own item containing:
      - id: schedule.external_id
      - descriptor: schedule name + charge item title/description
      - price: from charge_item_definition.price_components (with breakup)
      - fulfillment_id: single slot external_id this item is linked to
    """
    price = extract_price(schedule)
    cid = schedule.charge_item_definition

    descriptor = {
        "name": schedule.name,
        "code": "CONSULTATION",
    }
    if cid:
        descriptor["charge_item_desc"] = cid.title
        if cid.description:
            descriptor["charge_item_long_desc"] = cid.description

    return {
        "id": str(schedule.external_id),
        "descriptor": descriptor,
        "price": {
            "currency": price["currency"],
            "value": price["value"],
        },
        "fulfillment_id": fulfillment_id,
        "tags": [
            {
                "descriptor": {"code": "slot_type"},
                "list": [{"value": availability.slot_type}],
            },
            {
                "descriptor": {"code": "slot_duration_minutes"},
                "list": [{"value": str(availability.slot_size_in_minutes)}],
            },
        ],
    }


def build_catalog(
    facility: Facility,
    slots: list[TokenSlot],
    resource_map: dict[int, SchedulableResource],
    schedule_map: dict[int, tuple[Schedule, Availability]],
    fulfillment_type: str = FulfillmentType.physical.value,
) -> dict:

    provider = map_facility_to_provider(facility)

    items: list[dict] = []
    fulfillments: list[dict] = []

    for slot in slots:
        resource = resource_map.get(slot.resource_id)
        if not resource:
            continue

        sched_avail = schedule_map.get(slot.availability_id)
        if not sched_avail:
            continue

        schedule, availability = sched_avail

        # Only include slots that have remaining capacity
        tokens_per_slot = availability.tokens_per_slot or 1
        remaining = max(tokens_per_slot - slot.allocated, 0)
        if remaining == 0:
            continue

        fulfillment_id = str(slot.external_id)

        fulfillment = map_slot_to_fulfillment(slot, resource, fulfillment_type)
        fulfillment["id"] = fulfillment_id
        fulfillments.append(fulfillment)

        item = map_schedule_to_item(
            schedule, availability, fulfillment_id=fulfillment_id
        )
        items.append(item)

    provider["items"] = items
    provider["fulfillments"] = fulfillments

    return {
        "descriptor": CARE_CATALOG_DESCRIPTOR,
        "providers": [provider],
    }
