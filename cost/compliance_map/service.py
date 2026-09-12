"""cost/compliance_map — framework mapping only. Report language never says 'compliance'."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cost.db.store import dumps, fetch_all, init_schema
from cost.fixtures import tenant_id
from cost.paths import FRAMEWORKS_DIR
from cost.persist import persist_named

FRAMEWORK_FILES = {
    "finops-foundation": "finops-foundation.yaml",
    "aws-well-architected-cost": "aws-wa-cost.yaml",
    "azure-well-architected-cost": "azure-wa-cost.yaml",
    "gcp-architecture-cost": "gcp-arch-cost.yaml",
}


def run(*, sandbox: bool = True, framework: str = "finops-foundation", **_kwargs: Any) -> dict[str, Any]:
    key = framework.strip().lower()
    filename = FRAMEWORK_FILES.get(key, FRAMEWORK_FILES["finops-foundation"])
    path = FRAMEWORKS_DIR / filename
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    controls = list(spec.get("controls") or []) + list(spec.get("optimize_controls") or [])
    conn = init_schema()
    present = {
        "findings_costs": fetch_all(conn, "findings_costs", tenant_id()),
        "findings_rightsizing": fetch_all(conn, "findings_rightsizing", tenant_id()),
        "findings_untagged": fetch_all(conn, "findings_untagged", tenant_id()),
        "findings_drift": fetch_all(conn, "findings_drift", tenant_id()),
        "findings_resources": fetch_all(conn, "findings_resources", tenant_id()),
    }
    rows = []
    for control in controls:
        maps = list(control.get("maps_to") or [])
        observation_ids: list[str] = []
        for table in maps:
            for item in present.get(table) or []:
                observation_ids.append(str(item.get("resource_id") or item.get("service") or item.get("id") or table))
        status = "mapped" if observation_ids else "gap"
        if observation_ids and len(observation_ids) < 2:
            status = "partial"
        rows.append(
            {
                "tenant_id": tenant_id(),
                "framework": key,
                "control_id": control.get("id"),
                "control_name": control.get("name"),
                "status": status,
                "observation_ids": dumps(observation_ids[:12]),
            }
        )
    persist_named("findings_compliance", rows)
    return {
        "framework": key,
        "file": str(path),
        "rows": rows,
        "mapping_only": True,
        "honest_gap": "This is mapping, not an attestation.",
        "sandbox": sandbox,
        "attribution": spec.get("attribution", ""),
    }


def framework_path(name: str) -> Path:
    return FRAMEWORKS_DIR / FRAMEWORK_FILES.get(name, FRAMEWORK_FILES["finops-foundation"])
