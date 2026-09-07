"""Shared Pydantic models for DMARC findings tables."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DnsFinding(BaseModel):
    domain: str
    record_type: str
    value: str
    ttl: int | None = None
    last_checked_at: datetime


class SpfFinding(BaseModel):
    domain: str
    record: str
    dns_lookup_count: int
    lookups: list[str] = Field(default_factory=list)
    all_qualifier: str = "?"
    warnings: list[str] = Field(default_factory=list)


class DkimFinding(BaseModel):
    domain: str
    selector: str
    record: str
    public_key_length: int | None = None
    warnings: list[str] = Field(default_factory=list)


class DmarcAggregateFinding(BaseModel):
    domain: str
    source_org: str
    source_ip: str
    count: int
    disposition: str
    dkim_result: str
    spf_result: str
    date_range: str
    received_at: datetime


class ForensicFinding(BaseModel):
    domain: str
    source_ip: str
    from_address: str
    subject: str
    dkim_result: str
    spf_result: str
    received_at: datetime


class InboxFinding(BaseModel):
    provider: str
    seed_account: str
    placement: str
    subject: str
    from_address: str
    sent_at: datetime


class OssToolInfo(BaseModel):
    name: str
    version: str
    license: str
    module: str
    last_update: str = ""


def findings_to_rows(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
