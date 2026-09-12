"""Shadow data detection — heuristic unmanaged resources."""

from __future__ import annotations

import json
from pathlib import Path

from dspm.discovery.service import discover_cloud

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def scan_shadow() -> list[dict]:
    fixture = FIXTURES / "shadow_data.json"
    if fixture.exists():
        return json.loads(fixture.read_text(encoding="utf-8"))
    stores = discover_cloud("aws")
    shadows: list[dict] = []
    for s in stores:
        if "unmanaged" in s.location.lower() or "orphan" in s.location.lower():
            shadows.append(
                {
                    "resource": s.location,
                    "shadow_type": "unmanaged_bucket",
                    "confidence": 0.7,
                    "details": s.model_dump(),
                }
            )
    return shadows
