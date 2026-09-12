"""Pydantic models for cost/compliance_map."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModuleMeta(BaseModel):
    module: str = "compliance_map"
    kind: str = "cost-observation"


class FrameworkRow(BaseModel):
    control_id: str
    control_name: str
    status: str
    observation_ids: list[str] = Field(default_factory=list)
