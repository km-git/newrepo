"""DKIM finding rows."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DkimFinding(BaseModel):
    domain: str
    selector: str
    record: str
    public_key_length: int | None = None
    warnings: list[str] = Field(default_factory=list)
    last_checked_at: str = ""
