"""Markdown + JSON deliverability review (not a security assessment)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReportBundle(BaseModel):
    title: str = "Email Deliverability & Brand-Protection Review"
    domain: str
    markdown_path: str = ""
    json_path: str = ""
    sections: list[str] = Field(default_factory=list)
