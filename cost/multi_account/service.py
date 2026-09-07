"""Multi-account Cloud Custodian runner via c7n-org (fixture mode offline)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "c7n_org_output.json"


def run_accounts(
    *,
    accounts_yaml: Path | None = None,
    fixture: Path | None = None,
) -> dict[str, Any]:
    fx = fixture or FIXTURE
    data = json.loads(fx.read_text(encoding="utf-8"))
    return {
        "accounts_scanned": len(data.get("accounts", [])),
        "policies": data.get("policies", []),
        "output_tree": data.get("output_tree", "output/cost/c7n-org/"),
        "dryrun": True,
        "fixture": str(fx),
    }
