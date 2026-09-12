"""DMARC aggregate (RUA) finding rows."""

from __future__ import annotations

from pydantic import BaseModel


class DmarcFinding(BaseModel):
    domain: str
    source_org: str = ""
    source_ip: str = ""
    count: int = 0
    disposition: str = "none"
    dkim_result: str = "neutral"
    spf_result: str = "neutral"
    date_range: str = ""
    received_at: str = ""
