"""Google Workspace tenant discovery via Admin SDK / cnspec. No Gmail bodies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore
from sspm.discovery import discover as discover_tenant


def discover_gws(
    *,
    domain: str | None = None,
    service_account: str | None = None,
    tenant_name: str = "gws-demo",
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    _ = (domain, service_account)
    return discover_tenant(
        "gws",
        tenant_name=tenant_name or (domain or "gws-demo"),
        fixture=fixture,
        store=store,
    )
