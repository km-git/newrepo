"""Inbox placement finding rows."""

from __future__ import annotations

from pydantic import BaseModel


class InboxFinding(BaseModel):
    provider: str
    seed_account: str
    placement: str
    subject: str
    from_address: str
    sent_at: str
