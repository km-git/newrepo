"""Loop models (Discover / Evaluate / classify)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClassifyResult(BaseModel):
    finding_id: str
    client_summary: str
    reclaim_aud: float | None = None
    confidence: Literal["low", "medium", "high"]
    human_action: str = "draft email to manager, do not revoke"
    abstain: bool = False
    reason: str | None = None


class DiscoverItem(BaseModel):
    title: str
    url: str
    url_sha256: str
    module_hint: str = ""
    verdict: str = "skip"
    score: int = 0


class MonthlyRollup(BaseModel):
    as_of: str
    reclaim_monthly_aud: float
    unused_count: int
    trend: list[dict] = Field(default_factory=list)
