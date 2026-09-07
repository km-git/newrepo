"""OAuth grant inventory across discovered tenants."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "oauth_grants.json"


def _risk_level(scopes: str) -> str:
    scope_list = [s.strip().lower() for s in scopes.split(",") if s.strip()]
    write_scopes = [s for s in scope_list if "write" in s or "admin" in s or "delete" in s]
    if len(scope_list) > 5 or write_scopes:
        return "high"
    if len(scope_list) <= 1:
        return "low"
    return "medium"


def list_grants(
    tenant: str,
    fixture: str | None = None,
    store: FindingsStore | None = None,
) -> list[dict[str, Any]]:
    path = Path(fixture) if fixture else FIXTURE
    if not path.exists():
        grants = _default_grants(tenant)
    else:
        all_grants = json.loads(path.read_text(encoding="utf-8"))
        grants = all_grants.get(tenant, all_grants.get("m365", []))
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    for grant in grants:
        grant["risk_level"] = _risk_level(grant.get("scopes", ""))
        grant["tenant_type"] = tenant
        grant["observed_at"] = now
        if store:
            store.insert_oauth(
                {
                    "tenant_type": tenant,
                    "tenant_id": grant.get("tenant_id", tenant),
                    "app_name": grant["app_name"],
                    "publisher": grant.get("publisher", ""),
                    "scopes": grant.get("scopes", ""),
                    "last_used": grant.get("last_used"),
                    "risk_level": grant["risk_level"],
                    "observed_at": now,
                }
            )
    return grants


def _default_grants(tenant: str) -> list[dict[str, Any]]:
    return [
        {
            "tenant_id": f"demo-{tenant}",
            "app_name": "Salesforce",
            "publisher": "Salesforce Inc",
            "scopes": "User.Read, Mail.Read",
            "last_used": "2026-08-15T00:00:00Z",
        },
        {
            "tenant_id": f"demo-{tenant}",
            "app_name": "Legacy Sync Tool",
            "publisher": "Unknown",
            "scopes": "User.ReadWrite.All, Directory.ReadWrite.All, Mail.ReadWrite",
            "last_used": "2026-01-01T00:00:00Z",
        },
    ]
