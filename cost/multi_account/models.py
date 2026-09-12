"""Pydantic models for cost/multi_account."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "multi_account"
    kind: str = "cost-observation"


class AccountSlice(BaseModel):
    account_id: str
    provider: str
    policy: str
    finding_count: int = 0
