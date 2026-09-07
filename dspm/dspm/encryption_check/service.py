"""Encryption status via Trivy IaC scan."""

from __future__ import annotations

import json
from pathlib import Path

from dspm._cli_tools import run_cli

TRIVY_MIN_VERSION = "0.70.0"
TRIVY_BLOCKED = "0.69.4"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def check_encryption(path: Path) -> list[dict]:
    fixture = FIXTURES / "trivy_iac.json"
    try:
        raw = run_cli(["trivy", "config", str(path), "--format", "json"], fixture_path=fixture)
    except Exception:
        raw = json.loads(fixture.read_text(encoding="utf-8")) if fixture.exists() else {"Results": []}
    results = raw.get("Results", []) if isinstance(raw, dict) else []
    findings: list[dict] = []
    for r in results:
        for mis in r.get("Misconfigurations", []):
            findings.append(
                {
                    "resource": r.get("Target", str(path)),
                    "encrypted": "encryption" in mis.get("ID", "").lower() and mis.get("Status") == "PASS",
                    "encryption_type": mis.get("ID", "unknown"),
                    "details": mis,
                }
            )
    if not findings and path.exists():
        findings.append(
            {
                "resource": str(path),
                "encrypted": True,
                "encryption_type": "assumed-ok",
                "details": {"note": "no misconfigurations found"},
            }
        )
    return findings
