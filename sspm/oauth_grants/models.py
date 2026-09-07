"""OAuth grant row."""

from __future__ import annotations

from pydantic import BaseModel


class OAuthGrant(BaseModel):
    tenant_name: str
    tenant_type: str
    app_name: str
    publisher: str = ""
    scopes: str = ""
    last_used: str | None = None
    risk_level: str = "low"
