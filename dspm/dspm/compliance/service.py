"""Compliance framework mapping."""

from __future__ import annotations

from pathlib import Path

import yaml

from dspm.classification.service import classify_csv

CONTROLS_PATH = Path(__file__).resolve().parent / "controls.yaml"


def load_controls(framework: str) -> list[dict]:
    if not CONTROLS_PATH.exists():
        return _default_controls(framework)
    data = yaml.safe_load(CONTROLS_PATH.read_text(encoding="utf-8"))
    return data.get(framework, [])


def _default_controls(framework: str) -> list[dict]:
    base = {
        "gdpr": [
            {"control_id": "GDPR-32", "description": "Encryption of personal data", "finding_types": ["PII"]},
            {"control_id": "GDPR-25", "description": "Data protection by design", "finding_types": ["PII", "PHI"]},
        ],
        "hipaa": [
            {"control_id": "HIPAA-164.312", "description": "PHI access controls", "finding_types": ["PHI"]},
        ],
        "pci": [
            {"control_id": "PCI-3.4", "description": "Render PAN unreadable", "finding_types": ["PCI"]},
        ],
        "soc2": [
            {"control_id": "CC6.1", "description": "Logical access controls", "finding_types": ["PII", "secret"]},
        ],
    }
    return base.get(framework, [])


def map_compliance(framework: str, data_path: Path) -> list[dict]:
    findings = classify_csv(data_path)
    controls = load_controls(framework)
    mapped: list[dict] = []
    for f in findings:
        for ctrl in controls:
            if f.type in ctrl.get("finding_types", []):
                mapped.append(
                    {
                        "finding": f.model_dump(),
                        "framework": framework,
                        "control_id": ctrl["control_id"],
                        "status": "non_compliant" if f.confidence > 0.5 else "review",
                    }
                )
    return mapped
