
from uuid import UUID

from care.emr.models.organization import Organization
from care.emr.resources.base import PhoneNumber
from care.emr.resources.patient.spec import BloodGroupChoices, GenderChoices
from pydantic import BaseModel, Field, field_validator, model_validator

from care_uhi.resources.common import BecknContext

class Billing(BaseModel):
    name: str
    gender: GenderChoices
    phone_number: PhoneNumber = Field(max_length=14)
    emergency_phone_number: PhoneNumber | None = Field(None, max_length=14)
    address: str | None = None
    permanent_address: str | None = None
    pincode: int | None = None
    blood_group: BloodGroupChoices | None = None
    geo_organization: str

    @field_validator("geo_organization")
    @classmethod
    def validate_geo_organization(cls, geo_organization):
        if not Organization.objects.filter(
            org_type="govt", name__icontains=geo_organization
        ).exists():
            raise ValueError("Geo Organization does not exist")
        return geo_organization


class InitOrder(BaseModel):
    provider_id: UUID
    item_id: UUID
    fulfillment_id: UUID
    billing: Billing


class InitMessage(BaseModel):
    order: InitOrder


class InitRequest(BaseModel):
    """Full /init request payload."""

    context: BecknContext
    message: InitMessage

    @model_validator(mode="after")
    def validate_action(self):
        if self.context.action != "init":
            msg = f"Expected action 'init', got '{self.context.action}'"
            raise ValueError(msg)
        return self

