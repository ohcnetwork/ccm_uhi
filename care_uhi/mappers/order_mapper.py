from __future__ import annotations

from typing import TYPE_CHECKING

from care_uhi.mappers.catalog_mapper import (
    extract_price,
    map_facility_to_provider,
    map_schedule_to_item,
    map_slot_to_fulfillment,
)
from care_uhi.resources.common import OrderState

if TYPE_CHECKING:
    from care.emr.models.patient import Patient
    from care.emr.models.scheduling.booking import TokenBooking
    from care_uhi.models import BecknOrder


def map_patient_to_billing(patient: Patient) -> dict:
    """Patient → Beckn billing (patient details with external_id)."""
    return {
        "id": str(patient.external_id),
        "name": patient.name,
        "gender": patient.gender or "",
        "phone_number": patient.phone_number or "",
        "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else "",
        "address": patient.address or "",
    }


ORDER_STATUS_MAP = {
    OrderState.initialized.value: "initialized",
    OrderState.active.value: "active",
    OrderState.completed.value: "completed",
    OrderState.cancelled.value: "cancelled",
}


def map_booking_to_order(beckn_order: BecknOrder) -> dict:
    """
    Build a full Beckn order dict from a BecknOrder + its linked CARE booking.
    """
    booking = beckn_order.booking
    order = {
        "id": str(beckn_order.order_id),
        "status": ORDER_STATUS_MAP.get(beckn_order.status, "initialized"),
        "provider": {"id": beckn_order.provider_id},
        "items": [],
        "billing": beckn_order.billing,
        "quote": {"price": {"currency": "INR", "value": "0"}, "breakup": []},
        "terms": beckn_order.terms,
    }

    if booking:
        # Billing = patient details
        order["billing"] = map_patient_to_billing(booking.patient)

        slot = booking.token_slot
        if slot:
            resource = slot.resource
            facility = resource.facility
            order["provider"] = map_facility_to_provider(facility)

            availability = slot.availability
            schedule = availability.schedule if availability else None

            # Item with single fulfillment_id
            if schedule:
                order["items"] = [
                    map_schedule_to_item(schedule, availability, str(slot.external_id))
                ]
                # Quote from extract_price
                price_info = extract_price(schedule)
                order["quote"] = {
                    "price": {
                        "currency": price_info["currency"],
                        "value": price_info["value"],
                    },
                    "breakup": price_info.get("breakup", []),
                }

            # Fulfillment
            order["fulfillment"] = [map_slot_to_fulfillment(slot, resource)]

    return order


def build_terms() -> list[dict]:
    """Build informational terms for the consumer to review and agree upon in /confirm."""
    return [
        {
            "type": "cancellation",
            "descriptor": {"code": "CANCELLATION", "name": "Cancellation Policy"},
            "info": "Free cancellation up to 2 hours before the appointment. No refund for late cancellation.",
            "terms_state": "proposed",
        },
        {
            "type": "refund",
            "descriptor": {"code": "REFUND", "name": "Refund Policy"},
            "info": "Full refund if cancelled within the allowed period. Partial refund for no-shows.",
            "terms_state": "proposed",
        },
        {
            "type": "payment",
            "descriptor": {"code": "PAYMENT", "name": "Payment Terms"},
            "info": "Payment is collected at the facility before the consultation.",
            "terms_state": "proposed",
        },
        {
            "type": "settlement",
            "descriptor": {"code": "SETTLEMENT", "name": "Settlement Terms"},
            "info": "Settlement processed within 3 business days of consultation.",
            "terms_state": "proposed",
        },
    ]
