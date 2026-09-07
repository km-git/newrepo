"""Workspace + OSS tool inventory."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm import MODULES, OSS_PRIMARY_TOOLS, __version__
from sspm.constants import OSS_INVENTORY, PRESIDIO_SOURCE
from sspm.db.store import FindingsStore

ROOT = Path(__file__).resolve().parents[2]


def inventory(*, init_db: bool = True) -> dict[str, Any]:
    if init_db:
        FindingsStore()
    tools: list[dict[str, Any]] = []
    for item in OSS_INVENTORY:
        record = dict(item)
        record["on_path"] = bool(shutil.which(item["package"].split("[")[0]))
        tools.append(record)
    cnspec = shutil.which("cnspec")
    pip_audit_ok = False
    if shutil.which("pip-audit"):
        try:
            subprocess.run(
                ["pip-audit", "--version"],
                capture_output=True,
                check=True,
                timeout=10,
            )
            pip_audit_ok = True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    out_path = ROOT / "output" / "sspm" / "sspm-inventory.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
            "cnspec_on_path": bool(cnspec),
            "pip_audit_available": pip_audit_ok,
            "auto_merge_skips": ["sspm/disclaimers/", "sspm/loop/"],
        },
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
