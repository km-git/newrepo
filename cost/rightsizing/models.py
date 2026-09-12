"""Pydantic models for cost/rightsizing."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "rightsizing"
    kind: str = "cost-observation"


class RightsizingRow(BaseModel):
    resource_id: str
    current_type: str
    recommended_type: str
    monthly_savings_estimate: float
    risk_level: str
