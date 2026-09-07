"""Framework mapping — mapping only, not attestation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cost.constants import FRAMEWORKS
from cost.db.store import FindingsStore, utcnow

CONTROLS = Path(__file__).resolve().with_name("controls.yaml")


def map_findings(
    *,
    framework: str = "finops-foundation",
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    if framework not in FRAMEWORKS:
        raise ValueError(f"Unknown framework {framework}; choose from {list(FRAMEWORKS)}")
    controls_path = CONTROLS
    if not controls_path.exists():
        controls_path.write_text(
            yaml.safe_dump(
                {
                    "finops-foundation": [
                        {"control_id": "CFO-01", "title": "Inform — cost allocation tags"},
                        {"control_id": "CFO-02", "title": "Optimize — rightsizing review"},
                        {"control_id": "CFO-03", "title": "Operate — drift monitoring"},
                    ]
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    catalog = yaml.safe_load(controls_path.read_text(encoding="utf-8")) or {}
    controls = catalog.get(framework, [])
    db = store or FindingsStore()
    mapped = 0
    for ctrl in controls:
        db.insert(
            "findings_compliance",
            {
                "finding_ref": ctrl.get("title", ctrl["control_id"]),
                "framework": framework,
                "control_id": ctrl["control_id"],
                "mapping_status": "framework_reference",
                "mapped_at": utcnow(),
            },
        )
        mapped += 1
    return {
        "framework": framework,
        "framework_label": FRAMEWORKS[framework],
        "mapped_controls": mapped,
        "disclaimer": "Framework mapping only — not attestation.",
    }
