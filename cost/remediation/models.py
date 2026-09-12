"""Remediation policy models."""

from pydantic import BaseModel, Field


class RemediationAction(BaseModel):
    target: str
    action: str
    policy: str
    preconditions: list[str] = Field(default_factory=list)
    risk_level: str = "high"
    dry_run_safe: bool = True
    extra: dict = Field(default_factory=dict)
