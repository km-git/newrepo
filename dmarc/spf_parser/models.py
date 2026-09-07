"""SPF parse findings."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpfFinding(BaseModel):
    domain: str
    record: str
    dns_lookup_count: int
    lookups: list[str] = Field(default_factory=list)
    all_qualifier: str = ""
    warnings: list[str] = Field(default_factory=list)
    last_checked_at: str = ""
