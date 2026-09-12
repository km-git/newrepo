"""Config drift row."""

from __future__ import annotations

from pydantic import BaseModel


class DriftFinding(BaseModel):
    tenant_name: str
    tenant_type: str
    setting_name: str
    old_value: str | None
    new_value: str | None
    first_observed: str
    last_observed: str
    change_source: str = "unknown"
