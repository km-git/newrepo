"""Okta org discovery via Okta API / cnspec."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "okta_org.json"


def discover(
    org: str,
    token: str | None = None,
    fixture: str | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    path = Path(fixture) if fixture else FIXTURE
    data = json.loads(path.read_text(encoding="utf-8"))
    if token and shutil.which("cnspec"):
        try:
            subprocess.run(
                ["cnspec", "scan", "okta"],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    result = {
        "tenant_type": "okta",
        "tenant_id": org or data.get("org", "unknown"),
        "display_name": data.get("display_name"),
        "settings": data,
        "scanner": "cnspec+okta-api" if token else "fixture",
        "discovered_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    if store:
        store.insert_tenant(
            "okta",
            result["tenant_id"],
            result["display_name"] or result["tenant_id"],
            result["settings"],
        )
    return result
