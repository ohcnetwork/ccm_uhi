
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, field_validator


class BecknAction(str, Enum):
    search = "search"
    select = "select"
    init = "init"
    confirm = "confirm"
    status = "status"
    cancel = "cancel"


class FulfillmentType(str, Enum):
    online = "online"
    physical = "physical"


class TermsState(str, Enum):
    proposed = "proposed"
    agreed = "agreed"
    rejected = "rejected"


class OrderState(str, Enum):
    initialized = "initialized"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


TERMINAL_ORDER_STATES = {OrderState.cancelled.value, OrderState.completed.value}


class TransactionStatus(str, Enum):
    received = "received"
    processing = "processing"
    completed = "completed"
    error = "error"



class Descriptor(BaseModel):
    code: str
    name: str | None = None

class TimeTimestamp(BaseModel):
    timestamp: datetime


class TimeRange(BaseModel):
    time: TimeTimestamp

class Location(BaseModel):
    descriptor: Descriptor | None = None
    gps: str | None = None
    address: str | None = None
    city: dict | None = None

class Category(BaseModel):
    descriptor: Descriptor


class Price(BaseModel):
    currency: str = "INR"
    value: str = "0"


class Person(BaseModel):
    external_id: UUID4 | None = None
    name: str | None = None
    dob: str | None = None


class Contact(BaseModel):
    phone: str | None = None
    email: str | None = None


class Customer(BaseModel):
    person: Person | None = None
    contact: Contact | None = None

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, v):
        if v and not v.phone and not v.email:
            msg = "Customer must have at least phone or email"
            raise ValueError(msg)
        return v


class Billing(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_number: str | None = None

class TermType(str, Enum):
    commercial = "commercial"
    settlement = "settlement"
    cancellation = "cancellation"
    refund = "refund"
    payment = "payment"

class Term(BaseModel):
    type: TermType | None = None
    descriptor: Descriptor | None = None
    termsState: TermsState | None = None
    read_on: str | None = None
    period: str | None = None
    info: str | None = None


class Payment(BaseModel):
    collected_by: str | None = None
    type: str | None = None
    status: TransactionStatus | None = None
    params: dict | None = None


class QuoteBreakup(BaseModel):
    title: str | None = None
    price: Price | None = None


class Quote(BaseModel):
    price: Price | None = None
    breakup: list[QuoteBreakup] | None = None


# ── Context (common to ALL Beckn requests) ─────────────────────
class Domain(str, Enum):
    teleconsultation = "nic2004:85111"
    physical_consultation = "nic2004:85110"
    pmjay_hem = "nic2004:85112"
    blood_bank = "nic2004:85113"

class Country(str, Enum):
    india = "IND"

class BecknContext(BaseModel):

    domain: Domain
    country: Country
    city: str | None = None
    action: BecknAction
    version: str = "1.1.0"
    transaction_id: UUID4
    message_id: UUID4
    consumer_id: str
    consumer_uri: str
    provider_id: str | None = None
    provider_uri: str | None = None
    timestamp: datetime | None = None
    status: TransactionStatus | None = None

    @field_validator("provider_uri")
    @classmethod
    def validate_provider_uri(cls, v):
        if v and not v.startswith(("http://", "https://")):
            msg = "provider_uri must be a valid HTTP(S) URL"
            raise ValueError(msg)
        return v


class RequestContext(BaseModel):
    """Context sent by the EUA with every request."""
    message_id: str
    transaction_id: str


CORE_VERSION = "0.0.1"

def build_response_context(
    request_context: dict,
    action: str,
    facility=None,
) -> dict:
    """Build a response context echoing the EUA's message_id/timestamp
    and enriching with domain, country, city from the facility's geo_organization.
    """
    city = ""
    if facility and hasattr(facility, "geo_organization") and facility.geo_organization:
        city = str(facility.geo_organization.external_id)

    return {
        "domain": "nic2004:85110",
        "country": "IND",
        "city": city,
        "action": action,
        "core_version": CORE_VERSION,
        "message_id": request_context.get("message_id", ""),
        "transaction_id": request_context.get("transaction_id", ""),
    }
