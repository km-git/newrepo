"""Contract calendar models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class Contract(BaseModel):
    vendor: str
    seats: int
    renew_on: date
    notice_days: int
    amount_aud: float
    sku: str | None = None


class RenewalItem(BaseModel):
    vendor: str
    seats: int
    renew_on: date
    notice_by: date
    amount_aud: float
    days_until: int
    nudge: str


class RenewalReport(BaseModel):
    as_of: date
    window_days: int
    upcoming: list[RenewalItem] = Field(default_factory=list)
