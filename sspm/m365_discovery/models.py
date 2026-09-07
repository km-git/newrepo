"""Tenant snapshot models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Setting(BaseModel):
    name: str
    value: str
    source: str = "unknown"
    control_hint: str = ""


class TenantSnapshot(BaseModel):
    tenant_name: str
    tenant_type: str
    external_id: str | None = None
    display_name: str = ""
    scanner: str = "fixture"
    honest_gap: str = ""
    settings: list[Setting] = Field(default_factory=list)
    apps: list[dict] = Field(default_factory=list)
