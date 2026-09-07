"""Pydantic models for cost/azure_inventory."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModuleMeta(BaseModel):
    module: str = "azure_inventory"
    kind: str = "cost-observation"


class AzureResource(BaseModel):
    resource_id: str
    resource_type: str
    region: str
    monthly_cost: float = 0.0
    tags: dict[str, str] = Field(default_factory=dict)
