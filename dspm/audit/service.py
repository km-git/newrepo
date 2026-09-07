"""Workspace + tool inventory for the 12-module OSS DSPM mosaic."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dspm import MODULES, OSS_PRIMARY_TOOLS, __version__
from dspm.constants import OSS_INVENTORY, PRESIDIO_SOURCE, TRIVY_MALICIOUS, TRIVY_PIN
from dspm.db.store import FindingsStore
from dspm.tools import which

ROOT = Path(__file__).resolve().parents[2]


def inventory(*, init_db: bool = True) -> dict[str, Any]:
    if init_db:
        FindingsStore()
    tools = []
    for item in OSS_INVENTORY:
        record: dict[str, Any] = dict(item)
        binary = item["package"] if item["package"] in {"cloudquery", "steampipe", "trivy", "prowler"} else None
        if item["package"] == "c7n":
            binary = "c7n"
        record["on_path"] = bool(binary and which(binary))
        tools.append(record)
    return {
        "product": "dspm",
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
            "auto_merge_skips": ["dspm/remediation/policies/"],
        },
        "paths": {
            "schema": str(ROOT / "dspm" / "db" / "schema.sql"),
            "sample": str(ROOT / "examples" / "sample.csv"),
        },
    }
