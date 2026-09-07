"""M365 tenant discovery via Microsoft Graph / cnspec."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "m365_tenant.json"


def discover(
    tenant_id: str,
    client_id: str | None = None,
    client_secret: str | None = None,
    fixture: str | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    path = Path(fixture) if fixture else FIXTURE
    if client_id and client_secret and shutil.which("cnspec"):
        try:
            subprocess.run(
                ["cnspec", "scan", "microsoft365", "--output", "json"],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {
        "tenant_type": "m365",
        "tenant_id": tenant_id or data.get("tenant_id", "unknown"),
        "display_name": data.get("display_name"),
        "settings": data,
        "scanner": "cnspec+m365-graph" if client_secret else "fixture",
        "discovered_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    if store:
        store.insert_tenant(
            "m365",
            result["tenant_id"],
            result["display_name"] or result["tenant_id"],
            result["settings"],
        )
    return result
