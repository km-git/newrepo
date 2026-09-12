"""Okta org discovery. Custom apps reported as count + names."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore
from sspm.discovery import discover as discover_tenant


def discover_okta(
    *,
    org: str | None = None,
    token_env: str = "OKTA_TOKEN",
    tenant_name: str = "okta-demo",
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    _ = (org, token_env)
    return discover_tenant(
        "okta",
        tenant_name=tenant_name or (org or "okta-demo"),
        fixture=fixture,
        store=store,
    )
