"""cost/config_drift — cost-relevant config diffs (instance type, storage class, RI expiry)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cost.adapters import list_resources
from cost.fixtures import baseline_rows, tenant_id
from cost.persist import persist_named
from cost.subprocess_tools import CliUnavailable, prowler_snapshot


def _load_baseline(path: str) -> list[dict[str, Any]]:
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return list(data.get("baseline") or data.get("resources") or [])
    return baseline_rows()


def run(*, sandbox: bool = True, provider: str = "aws", baseline: str = "", **_kwargs: Any) -> dict[str, Any]:
    prowler_note = "prowler-unavailable-sandbox"
    if not sandbox:
        try:
            from cost.paths import PROWLER_OUT

            prowler_snapshot(provider if provider != "all" else "aws", PROWLER_OUT)
            prowler_note = "prowler-json"
        except (CliUnavailable, RuntimeError, FileNotFoundError, OSError):
            prowler_note = "prowler-unavailable-sandbox"

    resources: list[dict[str, Any]] = []
    providers = ("aws", "azure", "gcp") if provider == "all" else (provider,)
    for name in providers:
        chunk, _source = list_resources(name)
        resources.extend(chunk)
    by_id = {str(r.get("resource_id")): r for r in resources}
    findings = []
    for row in _load_baseline(baseline):
        rid = str(row.get("resource_id") or "")
        field = str(row.get("field") or "")
        expected = str(row.get("baseline") or "")
        current_item = by_id.get(rid) or {}
        cfg = current_item.get("config") or {}
        actual = str(cfg.get(field) or cfg.get("instance_type") or cfg.get("storage_class") or cfg.get("expiry") or "")
        if field == "instance_type":
            actual = str(cfg.get("instance_type") or actual)
        if field == "storage_class":
            actual = str(cfg.get("storage_class") or actual)
        if field == "expiry":
            actual = str(cfg.get("expiry") or actual)
        if expected and actual and expected != actual:
            findings.append(
                {
                    "tenant_id": tenant_id(),
                    "provider": current_item.get("provider") or provider,
                    "resource_id": rid,
                    "field": field,
                    "baseline": expected,
                    "current_value": actual,
                    "kind": row.get("kind") or field,
                }
            )
    persist_named("findings_drift", findings)
    return {
        "provider": provider,
        "findings": findings,
        "prowler": prowler_note,
        "sandbox": sandbox,
        "sql_engine": "sqlite",
    }
