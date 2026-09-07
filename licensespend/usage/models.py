"""Usage / unused-seat models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PriceSku(BaseModel):
    id: str
    vendor: str
    name: str
    monthly_aud: float


class UnusedSeat(BaseModel):
    user_id: str
    sku: str
    vendor: str
    idle_days: int | None
    monthly_cost: float
    department: str | None = None
    role: str = "member"
    email_hash: str | None = None
    email: str | None = None
    note: str | None = None
    last_active: date | None = None


class UnusedReport(BaseModel):
    as_of: date
    idle_days_threshold: int
    currency: str = "AUD"
    unused_count: int
    reclaim_monthly_aud: float
    rows: list[UnusedSeat] = Field(default_factory=list)
    abstained: list[str] = Field(default_factory=list)
    view: str = "v_unused_seats"
