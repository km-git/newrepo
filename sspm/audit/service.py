"""Workspace + tool inventory. Output: sspm-inventory.json."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm import MODULES, OSS_PRIMARY_TOOLS, __version__
from sspm.constants import DISALLOWED_AUTO_MERGE_PATHS, NO_STEAMPIPE, NO_TRIVY, OSS_INVENTORY, PRESIDIO_SOURCE
from sspm.db.store import FindingsStore

ROOT = Path(__file__).resolve().parents[2]


def inventory(*, init_db: bool = True, write: bool = True) -> dict[str, Any]:
    if init_db:
        FindingsStore()
    tools = []
    for item in OSS_INVENTORY:
        record = dict(item)
        binary = item["package"] if item["package"] in {"cnspec", "pip-audit"} else None
        record["on_path"] = bool(binary and shutil.which(binary))
        tools.append(record)
    payload = {
        "product": "sspm",
        "version": __version__,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "modules": list(MODULES),
        "primary_oss_tools": list(OSS_PRIMARY_TOOLS),
        "tool_count": len(tools),
        "tools": tools,
        "gates": {
            "presidio_source": PRESIDIO_SOURCE,
            "no_trivy": NO_TRIVY,
            "no_steampipe": NO_STEAMPIPE,
            "auto_merge_skips": list(DISALLOWED_AUTO_MERGE_PATHS),
            "report_kind": "Configuration & Inventory Report",
        },
        "paths": {
            "schema": str(Path(__file__).resolve().parents[1] / "db" / "schema.sql"),
            "fixtures": str(Path(__file__).resolve().parents[1] / "fixtures"),
        },
    }
    if write:
        dest = Path("output/sspm/sspm-inventory.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        payload["written"] = str(dest)
    return payload
