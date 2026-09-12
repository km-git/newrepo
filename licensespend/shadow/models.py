"""Shadow-SaaS finding models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ShadowApp(BaseModel):
    name: str
    source: str
    owner: str | None = None
    amount_aud: float | None = None
    in_pricebook: bool = False
    note: str | None = None


class ShadowReport(BaseModel):
    apps: list[ShadowApp] = Field(default_factory=list)
    honest_gap: str = "DNS/expense heuristics only. No CASB agent."
