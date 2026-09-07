"""Shared tenant discovery helpers: cnspec → live API → fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sspm.cnspec import scan as cnspec_scan
from sspm.db.store import FindingsStore, utcnow

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture(tenant_type: str) -> dict[str, Any]:
    path = FIXTURES / f"{tenant_type}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def persist_discovery(
    store: FindingsStore,
    *,
    tenant_name: str,
    tenant_type: str,
    payload: dict[str, Any],
) -> int:
    settings = payload.get("settings") or []
    tenant_id = store.insert(
        "findings_tenants",
        {
            "tenant_name": tenant_name,
            "tenant_type": tenant_type,
            "external_id": payload.get("external_id"),
            "display_name": payload.get("display_name") or tenant_name,
            "scanner": payload.get("scanner") or "fixture",
            "setting_count": len(settings),
            "extra": {
                "honest_gap": payload.get("honest_gap"),
                "apps": payload.get("apps") or [],
            },
            "discovered_at": utcnow(),
        },
    )
    for item in settings:
        store.insert(
            "findings_settings",
            {
                "tenant_name": tenant_name,
                "tenant_type": tenant_type,
                "setting_name": item["name"],
                "setting_value": str(item.get("value")),
                "source": item.get("source") or payload.get("scanner") or "fixture",
                "extra": {k: v for k, v in item.items() if k not in {"name", "value", "source"}},
                "observed_at": utcnow(),
            },
        )
    return tenant_id


def discover(
    tenant_type: str,
    *,
    tenant_name: str,
    live: dict[str, Any] | None = None,
    fixture: Path | None = None,
    store: FindingsStore | None = None,
    try_cnspec: bool = True,
) -> dict[str, Any]:
    cnspec = cnspec_scan(tenant_type) if try_cnspec else {"ok": False, "reason": "skipped"}
    if live:
        payload = dict(live)
        payload.setdefault("scanner", "api")
    elif fixture:
        payload = json.loads(Path(fixture).read_text(encoding="utf-8"))
        payload.setdefault("scanner", "fixture")
    else:
        payload = load_fixture(tenant_type)
        payload.setdefault("scanner", "fixture")
    if cnspec.get("ok"):
        payload["cnspec"] = cnspec
        payload["scanner"] = "cnspec"
    else:
        payload["cnspec"] = {"ok": False, "reason": cnspec.get("reason")}
    payload["tenant_name"] = tenant_name
    payload["tenant_type"] = tenant_type
    if store is not None:
        persist_discovery(store, tenant_name=tenant_name, tenant_type=tenant_type, payload=payload)
    return payload
