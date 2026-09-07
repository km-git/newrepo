"""Pydantic models for untagged."""

from pydantic import BaseModel, Field


class UntaggedResult(BaseModel):
    module: str = Field(default="untagged")
    ok: bool = True
    count: int = 0
