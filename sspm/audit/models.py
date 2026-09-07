"""Audit models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolRecord(BaseModel):
    name: str
    package: str
    version: str
    license: str
    role: str
    module: str
    install: str
    last_update: str
    on_path: bool = False


class Inventory(BaseModel):
    product: str = "sspm"
    version: str
    generated_at: str
    modules: list[str]
    tool_count: int
    tools: list[ToolRecord] = Field(default_factory=list)
    gates: dict[str, object] = Field(default_factory=dict)
