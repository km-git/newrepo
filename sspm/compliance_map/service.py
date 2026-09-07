"""Map observations to framework control references. Not an attestation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sspm.compliance_map.models import ControlReference
from sspm.db.store import FindingsStore, utcnow
from sspm.discovery import load_fixture

CONTROLS_PATH = Path(__file__).with_name("controls.yaml")

HARDENED_ON = {"true", "on", "required", "read", "365"}
HARDENED_OFF = {"false", "blocked", "restricted", "none", "existingexternalusersharingonly"}
INVERTED_HINTS = ("allowed", "public", "allowexternal", "lesssecure", "expirepasswords")


def load_controls(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or CONTROLS_PATH).read_text(encoding="utf-8")) or {}


def _matches(current: dict[str, str], setting: str, expected: str) -> bool:
    value = current.get(setting)
    if value is None:
        return False
    if expected == "any_hardened":
        lowered = value.lower()
        inverted = any(hint in setting.lower() for hint in INVERTED_HINTS)
        if inverted:
            return lowered in HARDENED_OFF
        return lowered in HARDENED_ON
    return str(value) == expected


def map_tenant(
    *,
    framework: str = "cis-m365",
    tenant: str = "m365",
    tenant_name: str | None = None,
    snapshot: dict[str, Any] | None = None,
    store: FindingsStore | None = None,
) -> list[ControlReference]:
    name = tenant_name or f"{tenant}-demo"
    snap = snapshot or load_fixture(tenant)
    current = {str(s["name"]): str(s.get("value")) for s in snap.get("settings") or []}
    controls = (load_controls().get("frameworks") or {}).get(framework.lower())
    if not controls:
        raise KeyError(f"unknown framework {framework!r}")
    hits: list[ControlReference] = []
    for control in controls:
        mapped = list(control.get("maps_to_settings") or [])
        expected = str(control.get("expected") or "")
        matched = [s for s in mapped if s in current]
        observed = [_matches(current, s, expected) for s in matched]
        if not matched:
            status = "not-observed"
        elif expected == "any_hardened":
            status = "matches-reference" if any(observed) else "differs-from-reference"
        else:
            status = "matches-reference" if all(observed) else "differs-from-reference"
        hit = ControlReference(
            tenant_name=name,
            tenant_type=tenant,
            framework=framework.lower(),
            control_id=str(control["control_id"]),
            title=str(control.get("title") or control["control_id"]),
            reference_status=status,
            matched_settings=matched,
        )
        hits.append(hit)
        if store is not None:
            store.insert(
                "findings_compliance",
                {
                    "tenant_name": name,
                    "tenant_type": tenant,
                    "framework": hit.framework,
                    "control_id": hit.control_id,
                    "title": hit.title,
                    "reference_status": hit.reference_status,
                    "extra": {"matched_settings": matched},
                    "mapped_at": utcnow(),
                },
            )
    return hits
