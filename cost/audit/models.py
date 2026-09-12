"""Pydantic models for cost/audit."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "audit"
    kind: str = "cost-observation"


class InventoryItem(BaseModel):
    name: str
    version: str
    license: str
    last_update: str
    invocation: str = "cli-subprocess"
