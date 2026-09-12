"""Pydantic models for cost/untagged."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "untagged"
    kind: str = "cost-observation"


class UntaggedRow(BaseModel):
    resource_id: str
    resource_type: str
    missing_tags: list[str]
    monthly_cost: float
