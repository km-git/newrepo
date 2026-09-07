"""Control-reference row (not an attestation)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ControlReference(BaseModel):
    tenant_name: str
    tenant_type: str
    framework: str
    control_id: str
    title: str
    reference_status: str
    matched_settings: list[str] = Field(default_factory=list)
