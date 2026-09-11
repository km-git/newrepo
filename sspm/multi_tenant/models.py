"""Tenant registry models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    name: str
    tenant_type: str
    client_id: str | None = None
    cron_expr: str = "0 9 * * 1"
    timezone: str = "Australia/Sydney"
    extra: dict = Field(default_factory=dict)
