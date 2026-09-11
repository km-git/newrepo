"""Pydantic models for cost/cost_explorer."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "cost_explorer"
    kind: str = "cost-observation"


class CostRow(BaseModel):
    provider: str
    service: str
    region: str
    amount: float
    period: str
