
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from care_uhi.resources.common import (
    BecknContext,
    TermsState,
)

VALID_CONFIRM_STATES = {TermsState.agreed, TermsState.rejected}

class Termtype(str, Enum):
    cancellation = "cancellation"
    refund = "refund"
    settlement = "settlement"
    commercial = "commercial"
    payment = "payment"

class ConfirmTerm(BaseModel):
    type: Termtype | None = None
    terms_state: TermsState


class ConfirmMessage(BaseModel):
    order_id: UUID
    terms: list[ConfirmTerm] = Field(default_factory=list)

    @field_validator("terms")
    @classmethod
    def validate_term_states(cls, v):
        for term in v:
            if term.terms_state not in VALID_CONFIRM_STATES:
                msg= f"Invalid terms_state '{term.terms_state}' for term type '{term.type}'"
                raise ValueError(msg)
        return v




class ConfirmRequest(BaseModel):
    """Full /confirm request payload."""

    context: BecknContext
    message: ConfirmMessage

    @model_validator(mode="after")
    def validate_action(self):
        if self.context.action != "confirm":
            msg = f"Expected action 'confirm', got '{self.context.action}'"
            raise ValueError(msg)
        return self
