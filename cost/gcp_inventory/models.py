"""Pydantic models for gcp_inventory."""

from pydantic import BaseModel, Field


class GcpInventoryResult(BaseModel):
    module: str = Field(default="gcp_inventory")
    ok: bool = True
    count: int = 0
