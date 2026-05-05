from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ccm_uhi.resources.common import BecknContext



class CancelMessage(BaseModel):
    order_id: UUID


class CancelRequest(BaseModel):
    """Full /cancel request payload."""

    context: BecknContext
    message: CancelMessage

    @model_validator(mode="after")
    def validate_action(self):
        if self.context.action != "cancel":
            msg = f"Expected action 'cancel', got '{self.context.action}'"
            raise ValueError(msg)
        return self
