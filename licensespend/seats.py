"""Seat and SKU models shared across connectors."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class Seat(BaseModel):
    user_id: str
    sku: str
    vendor: str
    last_active: date | None = None
    department: str | None = None
    role: str = "member"
    assigned: bool = True
    email_hash: str | None = None
    email: str | None = None
    note: str | None = None


class SkuCount(BaseModel):
    sku: str
    prepaid: int = 0
    consumed: int = 0


class SeatReport(BaseModel):
    vendor: str
    seats: list[Seat] = Field(default_factory=list)
    skus: list[SkuCount] = Field(default_factory=list)
    guests: int = 0
    outside_collaborators: int = 0
    honest_gap: str = ""
