"""Hand-maintained GDPR/HIPAA/PCI/SOC2 control mapping (honest gap vs Cyera)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dspm.compliance.models import ControlHit
from dspm.db.store import FindingsStore, utcnow

CONTROLS_PATH = Path(__file__).with_name("controls.yaml")


def load_controls(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or CONTROLS_PATH).read_text(encoding="utf-8")) or {}


def map_findings(
    findings: list[dict[str, Any]],
    *,
    framework: str = "gdpr",
    store: FindingsStore | None = None,
) -> list[ControlHit]:
    controls = (load_controls().get("frameworks") or {}).get(framework.lower())
    if not controls:
        raise KeyError(f"unknown framework {framework!r}")
    hits: list[ControlHit] = []
    types_present = {str(row.get("type")) for row in findings}
    for control in controls:
        mapped = set(control.get("maps_to_types") or [])
        matched = sorted(types_present & mapped)
        status = "FAIL" if matched else "PASS"
        hits.append(
            ControlHit(
                framework=framework.lower(),
                control_id=str(control["control_id"]),
                title=str(control.get("title") or control["control_id"]),
                status=status,
                matched_types=matched,
            )
        )
        if store is not None:
            store.insert(
                "findings_compliance",
                {
                    "finding_id": None,
                    "framework": framework.lower(),
                    "control_id": control["control_id"],
                    "status": status,
                    "extra": {"matched_types": matched, "title": control.get("title")},
                    "mapped_at": utcnow(),
                },
            )
    return hits
