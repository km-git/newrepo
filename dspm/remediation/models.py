from typing import Any

from pydantic import BaseModel, Field


class RemediationAction(BaseModel):
    target: str
    action: str
    policy: str
    preconditions: list[str] = Field(default_factory=list)
    risk_level: str
    dry_run_safe: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)
