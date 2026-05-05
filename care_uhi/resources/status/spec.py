
from __future__ import annotations
from uuid import UUID

from pydantic import BaseModel, model_validator

from care_uhi.resources.common import BecknContext


class StatusMessage(BaseModel):
    order_id: UUID

class StatusRequest(BaseModel):
    """Full /status request payload."""

    context: BecknContext
    message: StatusMessage

    @model_validator(mode="after")
    def validate_action(self):
        if self.context.action != "status":
            msg = f"Expected action 'status', got '{self.context.action}'"
            raise ValueError(msg)
        return self
