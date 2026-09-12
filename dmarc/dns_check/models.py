"""DNS finding rows."""

from __future__ import annotations

from pydantic import BaseModel


class DnsFinding(BaseModel):
    domain: str
    record_type: str
    value: str
    ttl: int | None = None
    last_checked_at: str
