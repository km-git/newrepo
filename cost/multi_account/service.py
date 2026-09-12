"""cost/multi_account — aggregate c7n-org dry-run trees (never live destructive)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cost.paths import PACKAGE_ROOT
from cost.subprocess_tools import CliUnavailable, run_cli


def run(*, sandbox: bool = True, accounts: str = "", **_kwargs: Any) -> dict[str, Any]:
    path = Path(accounts) if accounts else PACKAGE_ROOT / "accounts.example.yaml"
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = list(spec.get("accounts") or [])
    c7n_note = "c7n-org-unavailable-sandbox"
    if not sandbox:
        try:
            run_cli("c7n-org", ["run", "-c", str(path), "-s", "output/cost/c7n-org", "--dryrun"], timeout=60)
            c7n_note = "c7n-org-dryrun"
        except (CliUnavailable, RuntimeError, OSError):
            c7n_note = "c7n-org-unavailable-sandbox"
    return {
        "accounts": rows,
        "account_count": len(rows),
        "c7n_org": c7n_note,
        "dryrun": True,
        "sandbox": sandbox,
    }
