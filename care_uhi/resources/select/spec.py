
from uuid import UUID

from pydantic import BaseModel, model_validator

from care_uhi.resources.common import BecknContext




class SelectOrder(BaseModel):
    provider_id: UUID
    item_id: UUID
    fulfillment_id: UUID


class SelectMessage(BaseModel):
    order: SelectOrder


class SelectRequest(BaseModel):
    """Full /select request payload."""

    context: BecknContext
    message: SelectMessage

    @model_validator(mode="after")
    def validate_action(self):
        if self.context.action != "select":
            msg = f"Expected action 'select', got '{self.context.action}'"
            raise ValueError(msg)
        return self
