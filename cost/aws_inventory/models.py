"""Pydantic models for aws_inventory."""

from pydantic import BaseModel, Field


class AwsInventoryResult(BaseModel):
    module: str = Field(default="aws_inventory")
    ok: bool = True
    count: int = 0
