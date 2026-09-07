"""Multi-tenant registry and scheduling."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from croniter import croniter

REGISTRY = Path(__file__).resolve().parents[1] / "tenants.yaml"


def _load() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {"tenants": []}
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {"tenants": []}


def _save(data: dict[str, Any]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def add_tenant(
    name: str,
    tenant_type: str,
    client_id: str | None = None,
    schedule_cron: str = "0 9 * * 1",
) -> dict[str, Any]:
    data = _load()
    entry = {
        "name": name,
        "type": tenant_type,
        "client_id": client_id,
        "schedule_cron": schedule_cron,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    data["tenants"] = [t for t in data["tenants"] if t.get("name") != name]
    data["tenants"].append(entry)
    _save(data)
    return entry


def list_tenants() -> list[dict[str, Any]]:
    tenants = _load().get("tenants", [])
    enriched = []
    for t in tenants:
        cron = t.get("schedule_cron", "0 9 * * 1")
        try:
            next_run = croniter(cron, datetime.now(UTC)).get_next(datetime).isoformat()
        except Exception:
            next_run = None
        enriched.append({**t, "next_scheduled_run": next_run})
    return enriched
