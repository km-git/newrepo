"""Pydantic models for rightsizing."""

from pydantic import BaseModel, Field


class RightsizingResult(BaseModel):
    module: str = Field(default="rightsizing")
    ok: bool = True
    count: int = 0
