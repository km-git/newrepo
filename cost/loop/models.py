"""Pydantic models for cost/loop."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "loop"
    kind: str = "cost-observation"


class DiscoverItem(BaseModel):
    title: str
    url: str
    module: str = "unknown"
