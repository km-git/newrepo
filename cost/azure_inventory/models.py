"""Pydantic models for azure_inventory."""

from pydantic import BaseModel, Field


class AzureInventoryResult(BaseModel):
    module: str = Field(default="azure_inventory")
    ok: bool = True
    count: int = 0
