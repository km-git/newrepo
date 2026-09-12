"""Pydantic models for cost/config_drift."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "config_drift"
    kind: str = "cost-observation"


class DriftRow(BaseModel):
    resource_id: str
    field: str
    baseline: str
    current: str
