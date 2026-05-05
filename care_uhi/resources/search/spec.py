"""
Pydantic spec for Beckn /search request.

Validates the incoming search intent:
- provider_id (facility external_id)
- fulfillment type and time window
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator

from care_uhi.resources.common import (
    BecknContext,
    FulfillmentType,
    TimeRange,
)
from care.utils.time_util import care_now


class SearchFulfillment(BaseModel):
    type: FulfillmentType
    start: TimeRange
    end: TimeRange

    @model_validator(mode="after")
    def validate_time_window(self):
        if self.start and self.end:
            if self.start.time.timestamp < care_now():
                msg = "Fulfillment start time must not be in the past"
                raise ValueError(msg)
            if self.end.time.timestamp <= self.start.time.timestamp:
                msg = "Fulfillment end time must be after start time"
                raise ValueError(msg)
        return self


class SearchIntent(BaseModel):
    provider_id: UUID | None = None
    fulfillment: SearchFulfillment | None = None


class SearchMessage(BaseModel):
    intent: SearchIntent


class SearchRequest(BaseModel):
    """Full /search request payload."""

    context: BecknContext
    message: SearchMessage

    @model_validator(mode="after")
    def validate_action(self):
        if self.context.action != "search":
            msg = f"Expected action 'search', got '{self.context.action}'"
            raise ValueError(msg)
        return self
