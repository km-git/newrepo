"""Audit models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolRecord(BaseModel):
    name: str
    package: str
    license: str
    role: str
    extra: str | None = None
    on_path: bool = False
    version: str | None = None


class Inventory(BaseModel):
    product: str = "licensespend"
    version: str
    modules: list[str]
    tool_count: int
    tools: list[ToolRecord] = Field(default_factory=list)
    pip_audit: dict = Field(default_factory=dict)
    gates: dict = Field(default_factory=dict)
