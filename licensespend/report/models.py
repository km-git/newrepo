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
    unused_count: int = 0
    seats_total: int = 0
    idle_days_threshold: int = 90
    reclaim_monthly_aud: float = 0.0
    reclaim_annual_aud: float = 0.0
    vendor_breakdown: list[dict] = Field(default_factory=list)
    department_breakdown: list[dict] = Field(default_factory=list)
    idle_buckets: dict[str, int] = Field(default_factory=dict)
    renewals: list[dict] = Field(default_factory=list)
    shadow_apps: list[dict] = Field(default_factory=list)
    reclaim_appendix: list[dict] = Field(default_factory=list)
    sku_economics: list[dict] = Field(default_factory=list)
    idle_sensitivity: list[dict] = Field(default_factory=list)
    draft_actions: list[dict] = Field(default_factory=list)
    qbr_talk_track: list[str] = Field(default_factory=list)
    honest_gaps: list[str] = Field(default_factory=list)
    watermark: str = ""
    draft: bool = True
    disclaimer: str = "Draft reclaim pack for human review. Not regulated advice. Do not auto-revoke."
