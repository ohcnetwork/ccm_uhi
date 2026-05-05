"""
OnSelectService: Handles Beckn /on_select callback.

Resolves the selected provider (facility), items (schedules), and
fulfillments (slots), then returns item details, fulfillment info,
and a quote with price breakup.
"""

import logging

from care.emr.models.scheduling.booking import TokenSlot
from care.emr.models.scheduling.schedule import Availability, Schedule
from care_uhi.mappers.catalog_mapper import (
    extract_price,
    map_facility_to_provider,
    map_schedule_to_item,
    map_slot_to_fulfillment,
    resolve_facility,
)

logger = logging.getLogger(__name__)


class OnSelectService:
    """Process a Beckn select request and return order with items, fulfillment, and quote."""

    def execute(self, context: dict, message: dict) -> dict:
        order_msg = message.get("order", {})
        provider_id = order_msg.get("provider_id", "")
        item_id = order_msg.get("item_id", "")
        fulfillment_id = order_msg.get("fulfillment_id", "")

        if not provider_id:
            msg = "Provider provider_id is required"
            raise ValueError(msg)

        if not item_id:
            msg = "Item ID is required"
            raise ValueError(msg)

        if not fulfillment_id:
            msg = "Fulfillment ID is required"
            raise ValueError(msg)

        facility = resolve_facility(provider_id)

        result_items = []
        fulfillments = []
        quote_breakup = []
        total_price = 0.0

        slot = self._resolve_slot(fulfillment_id)
        schedule, availability = self._resolve_schedule(slot)

        if item_id and str(schedule.external_id) != str(item_id):
            msg = f"Item {item_id} does not match schedule for the given slot"
            raise ValueError(msg)

        if slot.resource.facility_id != facility.id:
            msg = "Slot does not belong to the requested provider"
            raise ValueError(msg)

        self._validate_slot_availability(slot)

        resource = slot.resource

            # Build item using shared mapper
        result_items.append(
            map_schedule_to_item(schedule, availability, str(slot.external_id))
            )

            # Build fulfillment using shared mapper
        fulfillments.append(map_slot_to_fulfillment(slot, resource))

            # Accumulate quote from full price (includes breakup)
        price_info = extract_price(schedule)
        total_price += float(price_info.get("value", 0))
        quote_breakup.extend(price_info.get("breakup", []))

        quote = {
            "price": {
                "currency": "INR",
                "value": str(round(total_price, 2)),
            },
            "breakup": quote_breakup,
        }

        return {
            "order":{
                "provider": map_facility_to_provider(facility),
                "items": result_items,
                "fulfillments": fulfillments,
                "quote": quote,
                }
            }

    def _resolve_slot(self, fulfillment_id: str) -> TokenSlot:
        try:
            return TokenSlot.objects.select_related(
                "resource",
                "resource__user",
                "resource__facility",
                "availability",
                "availability__schedule",
                "availability__schedule__charge_item_definition",
            ).get(external_id=fulfillment_id, deleted=False)
        except TokenSlot.DoesNotExist:
            msg = f"Fulfillment (slot) {fulfillment_id} not found"
            raise ValueError(msg)

    def _resolve_schedule(
        self, slot: TokenSlot
    ) -> tuple[Schedule, Availability]:
        availability = slot.availability
        if not availability:
            msg = f"Slot {slot.external_id} has no linked availability"
            raise ValueError(msg)

        schedule = availability.schedule
        if not schedule:
            msg = f"Availability {availability.id} has no linked schedule"
            raise ValueError(msg)

        return schedule, availability

    def _validate_slot_availability(self, slot: TokenSlot) -> None:
        if slot.availability and slot.availability.tokens_per_slot:
            if slot.allocated >= slot.availability.tokens_per_slot:
                msg = f"Slot {slot.external_id} is fully booked"
                raise ValueError(msg)
