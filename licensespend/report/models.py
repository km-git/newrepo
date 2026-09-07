"""Reclaim-pack report models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReportFiles(BaseModel):
    json_path: str
    markdown_path: str
    html_path: str
    watermark: str
    client: str
    reclaim_monthly_aud: float
    unused_count: int
    emails_included: bool = False


class ReportPayload(BaseModel):
    product: str = "licensespend"
    client: str
    as_of: str
    seats_bought: dict = Field(default_factory=dict)
    seats_used: dict = Field(default_factory=dict)
    unused: list[dict] = Field(default_factory=list)
    reclaim_monthly_aud: float = 0.0
    renewals: list[dict] = Field(default_factory=list)
    shadow_apps: list[dict] = Field(default_factory=list)
    reclaim_appendix: list[dict] = Field(default_factory=list)
    watermark: str = ""
    draft: bool = True
    disclaimer: str = "Draft reclaim pack for human review. Not regulated advice. Do not auto-revoke."
