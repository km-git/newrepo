"""Multi-tenant registry (tenants.yaml) + per-tenant Monday/Tuesday AEST cron."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sspm.db.store import FindingsStore, utcnow
from sspm.multi_tenant.models import Tenant

DEFAULT_REGISTRY = Path("output/sspm/tenants.yaml")

# Stay under the GitHub Actions 256-job-per-workflow cap by spreading tenants.
DEFAULT_CRONS = {
    "m365": "0 9 * * 1",
    "gws": "0 9 * * 2",
    "github": "0 9 * * 3",
    "slack": "0 9 * * 4",
    "okta": "0 9 * * 5",
}


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("tenants") or [])


def _save(path: Path, tenants: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"tenants": tenants}, sort_keys=False), encoding="utf-8")


def add_tenant(
    *,
    name: str,
    tenant_type: str,
    client_id: str | None = None,
    cron_expr: str | None = None,
    registry: Path | None = None,
    store: FindingsStore | None = None,
) -> Tenant:
    path = registry or DEFAULT_REGISTRY
    tenants = _load(path)
    if any(t.get("name") == name for t in tenants):
        raise ValueError(f"tenant {name!r} already registered")
    tenant = Tenant(
        name=name,
        tenant_type=tenant_type,
        client_id=client_id,
        cron_expr=cron_expr or DEFAULT_CRONS.get(tenant_type, "0 9 * * 1"),
    )
    row = tenant.model_dump()
    tenants.append(row)
    _save(path, tenants)
    if store is not None:
        store.insert(
            "tenants",
            {
                "name": tenant.name,
                "tenant_type": tenant.tenant_type,
                "client_id": tenant.client_id,
                "cron_expr": tenant.cron_expr,
                "timezone": tenant.timezone,
                "extra": tenant.extra,
                "created_at": utcnow(),
            },
        )
    return tenant


def list_tenants(registry: Path | None = None) -> list[Tenant]:
    return [Tenant(**row) for row in _load(registry or DEFAULT_REGISTRY)]


def next_run(cron_expr: str, timezone: str = "Australia/Sydney") -> str:
    try:
        from datetime import datetime

        from croniter import croniter

        try:
            from zoneinfo import ZoneInfo

            now = datetime.now(ZoneInfo(timezone))
        except Exception:
            now = datetime.now()
        return croniter(cron_expr, now).get_next(datetime).isoformat()
    except ImportError:
        return f"cron:{cron_expr} tz:{timezone}"
