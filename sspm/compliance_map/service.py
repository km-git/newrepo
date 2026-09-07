"""Map findings to control references (not attestation)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CONTROLS = Path(__file__).resolve().parent / "controls.yaml"


def map_framework(
    framework: str,
    tenant: str,
    findings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    controls = yaml.safe_load(CONTROLS.read_text(encoding="utf-8"))
    fw = controls.get(framework, {})
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    if findings is None:
        findings = [{"id": "demo-1", "type": "mfa_enforced", "value": True}]
    mapped: list[dict[str, Any]] = []
    for finding in findings:
        ftype = str(finding.get("type", ""))
        for control_id, meta in fw.items():
            if ftype in meta.get("matches", []):
                mapped.append(
                    {
                        "tenant_type": tenant,
                        "framework": framework,
                        "control_id": control_id,
                        "control_reference": meta.get("title", control_id),
                        "finding_ref": finding.get("id"),
                        "mapped_at": now,
                        "note": "control reference only — not a control status",
                    }
                )
    return mapped
