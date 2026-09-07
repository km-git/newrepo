"""Shared Pydantic models for DSPM modules."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Finding(BaseModel):
    source: str
    location: str
    type: str
    confidence: float = Field(ge=0.0, le=1.0)
    verdict: str
    suggested_action: str | None = None


class StoreFinding(BaseModel):
    source: str
    location: str
    provider: str | None = None
    store_type: str | None = None


class RiskScore(BaseModel):
    finding_id: int
    score: float = Field(ge=0.0, le=100.0)
    vector: str
    suggested_action: str | None = None


class RemediationAction(BaseModel):
    target: str
    action: str
    preconditions: dict[str, Any] = Field(default_factory=dict)
    risk_level: str
    dry_run_safe: bool = True


class OssToolInfo(BaseModel):
    name: str
    version: str
    license: str
    module: str
    last_update: str | None = None
