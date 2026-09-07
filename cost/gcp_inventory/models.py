"""Pydantic models for cost/gcp_inventory."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModuleMeta(BaseModel):
    module: str = "gcp_inventory"
    kind: str = "cost-observation"


class GcpResource(BaseModel):
    resource_id: str
    resource_type: str
    region: str
    monthly_cost: float = 0.0
    tags: dict[str, str] = Field(default_factory=dict)
