"""Forensic (RUF) finding rows."""

from __future__ import annotations

from pydantic import BaseModel


class ForensicFinding(BaseModel):
    domain: str
    source_ip: str = ""
    from_address: str = ""
    subject: str = ""
    dkim_result: str = "neutral"
    spf_result: str = "neutral"
    received_at: str = ""
