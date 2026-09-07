"""Exposure detection via Prowler + Steampipe fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from dspm._cli_tools import run_cli

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def scan_exposure(provider: str = "aws") -> list[dict]:
    fixture = FIXTURES / f"prowler_{provider}.json"
    try:
        raw = run_cli(
            ["prowler", provider, "--severity", "high", "critical", "--output-formats", "json"],
            fixture_path=fixture,
        )
    except Exception:
        raw = json.loads(fixture.read_text(encoding="utf-8")) if fixture.exists() else []
    if isinstance(raw, dict):
        items = raw.get("findings", raw.get("AssessmentResults", []))
    else:
        items = raw
    exposures: list[dict] = []
    for item in items:
        exposures.append(
            {
                "resource": item.get("resource", item.get("ResourceId", "unknown")),
                "exposure_type": item.get("check_title", item.get("type", "misconfiguration")),
                "severity": item.get("severity", item.get("Severity", "high")),
                "details": item,
            }
        )
    return exposures
