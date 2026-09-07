"""Workspace + OSS tool inventory."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cost import MODULES, OSS_PRIMARY_TOOLS, __version__
from cost.constants import OSS_INVENTORY, PRESIDIO_SOURCE, TRIVY_MALICIOUS, TRIVY_PIN
from cost.db.store import FindingsStore
from cost.tools import trivy_version_ok, which

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "output" / "cost" / "cost-inventory.json"


def inventory(*, init_db: bool = True, write_json: bool = True) -> dict[str, Any]:
    if init_db:
        FindingsStore()
    tools = []
    for item in OSS_INVENTORY:
        record: dict[str, Any] = dict(item)
        binary = (
            item["package"]
            if item["package"]
            in {
                "steampipe",
                "prowler",
                "trivy",
                "c7n",
                "c7n-org",
            }
            else None
        )
        record["on_path"] = bool(binary and which(binary))
        tools.append(record)
    payload = {
        "product": "cost",
        "version": __version__,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "modules": list(MODULES),
        "primary_oss_tools": list(OSS_PRIMARY_TOOLS),
        "tool_count": len(tools),
        "tools": tools,
        "gates": {
            "presidio_source": PRESIDIO_SOURCE,
            "trivy_pin": TRIVY_PIN,
            "trivy_refused": sorted(TRIVY_MALICIOUS),
            "steampipe_linkage": "cli-subprocess-only",
            "auto_merge_skips": ["cost/remediation/policies/"],
            "trivy_ok": trivy_version_ok(),
        },
        "paths": {
            "schema": str(ROOT / "cost" / "db" / "schema.sql"),
            "disclaimer": str(ROOT / "disclaimers" / "disclaimer_au.txt"),
        },
    }
    if write_json:
        INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        INVENTORY_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["inventory_path"] = str(INVENTORY_PATH)
    return payload
