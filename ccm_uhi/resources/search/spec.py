"""
Pydantic spec for /search request.

Search is now a GET endpoint with optional query parameters:
- provider_id: optional filter to a specific facility
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SearchParams(BaseModel):
    """Query parameters for the search GET endpoint."""
    provider_id: UUID | None = None
