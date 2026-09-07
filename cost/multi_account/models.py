"""Pydantic models for multi_account."""

from pydantic import BaseModel, Field


class MultiAccountResult(BaseModel):
    module: str = Field(default="multi_account")
    ok: bool = True
    count: int = 0
