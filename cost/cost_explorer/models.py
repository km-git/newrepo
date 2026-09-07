"""Pydantic models for cost_explorer."""

from pydantic import BaseModel, Field


class CostExplorerResult(BaseModel):
    module: str = Field(default="cost_explorer")
    ok: bool = True
    count: int = 0
