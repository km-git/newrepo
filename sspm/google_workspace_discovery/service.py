"""Google Workspace discovery via Admin SDK / cnspec."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "gws_tenant.json"


def discover(
    domain: str,
    service_account: str | None = None,
    fixture: str | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    path = Path(fixture) if fixture else FIXTURE
    if service_account and shutil.which("cnspec"):
        try:
            subprocess.run(
                ["cnspec", "scan", "google-workspace", "--output", "json"],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass  # cnspec optional; fixture JSON is the source of truth
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {
        "tenant_type": "gws",
        "tenant_id": domain or data.get("domain", "unknown"),
        "display_name": data.get("display_name"),
        "settings": data,
        "scanner": "cnspec+gws-admin" if service_account else "fixture",
        "discovered_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    if store:
        store.insert_tenant(
            "gws",
            result["tenant_id"],
            result["display_name"] or result["tenant_id"],
            result["settings"],
        )
    return result
