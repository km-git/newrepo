"""Report models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReportFiles(BaseModel):
    markdown: str
    json_path: str
    html: str | None = None
    sha256: str
    title: str = "Configuration & Inventory Report"
    forbidden_hits: list[str] = Field(default_factory=list)
