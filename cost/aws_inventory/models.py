"""Pydantic models for cost/aws_inventory."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModuleMeta(BaseModel):
    module: str = "aws_inventory"
    kind: str = "cost-observation"


class AwsResource(BaseModel):
    resource_id: str
    resource_type: str
    region: str
    monthly_cost: float = 0.0
    tags: dict[str, str] = Field(default_factory=dict)
