"""Pydantic models for config_drift."""

from pydantic import BaseModel, Field


class ConfigDriftResult(BaseModel):
    module: str = Field(default="config_drift")
    ok: bool = True
    count: int = 0
