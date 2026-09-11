"""Aggregate report rows (reuses findings_dmarc)."""

from __future__ import annotations

from pydantic import BaseModel


class SourceSummary(BaseModel):
    source_org: str
    source_ip: str
    count: int
    pass_count: int
    fail_count: int
    pass_rate: float
