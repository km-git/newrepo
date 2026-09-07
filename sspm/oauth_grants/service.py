"""OAuth grant inventory. Runtime behaviour of apps is out of scope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore, utcnow
from sspm.oauth_grants.models import OAuthGrant

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "oauth.json"

OVERSCOPED_HINTS = (
    "directory.readwrite",
    "mail.read",
    "files.readwrite",
    "drive",
    "repo",
    "groups.manage",
    "okta.users",
)


def risk_for_scopes(scopes: str) -> str:
    blob = scopes.lower()
    scope_parts = [part for part in blob.replace(",", " ").split() if part]
    overscoped = any(hint in blob for hint in OVERSCOPED_HINTS)
    if overscoped or "repo" in blob or "/auth/drive" in blob:
        return "high"
    if len(scope_parts) <= 1:
        return "low"
    if len(scope_parts) >= 4:
        return "high"
    return "medium"


def list_grants(
    *,
    tenant: str = "m365",
    tenant_name: str | None = None,
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> list[OAuthGrant]:
    _ = fixture
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = []
    for item in data.get("grants") or []:
        if tenant not in {"all", item.get("tenant_type")}:
            continue
        scopes = str(item.get("scopes") or "")
        grant = OAuthGrant(
            tenant_name=tenant_name or f"{item.get('tenant_type')}-demo",
            tenant_type=str(item.get("tenant_type")),
            app_name=str(item.get("app_name")),
            publisher=str(item.get("publisher") or ""),
            scopes=scopes,
            last_used=item.get("last_used"),
            risk_level=str(item.get("risk_level") or risk_for_scopes(scopes)),
        )
        rows.append(grant)
        if store is not None:
            store.insert(
                "findings_oauth",
                {
                    **grant.model_dump(),
                    "extra": {},
                    "observed_at": utcnow(),
                },
            )
    return rows


def list_grants_dicts(**kwargs: Any) -> list[dict[str, Any]]:
    return [g.model_dump() for g in list_grants(**kwargs)]
