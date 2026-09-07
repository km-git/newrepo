"""Heuristic shadow-data detection (unmanaged buckets, forgotten DBs). Not ML."""

from __future__ import annotations

from dspm.db.store import FindingsStore, utcnow
from dspm.discovery.models import Store
from dspm.discovery.service import discover_cloud, discover_directory
from dspm.shadow.models import ShadowAsset


def scan_shadow(
    *,
    path: str | None = None,
    provider: str = "aws",
    store: FindingsStore | None = None,
) -> list[ShadowAsset]:
    assets: list[Store] = []
    if path:
        assets.extend(discover_directory(path))
    assets.extend(discover_cloud(provider))
    shadows: list[ShadowAsset] = []
    for item in assets:
        unmanaged = not item.managed or "unmanaged" in item.name.lower() or "shadow" in item.location.lower()
        orphan = "snapshot" in item.kind.lower() or "snapshot" in item.name.lower()
        if not (unmanaged or orphan):
            continue
        reason = "unmanaged store" if unmanaged else "orphaned snapshot"
        shadows.append(
            ShadowAsset(
                location=item.location,
                kind=item.kind,
                reason=reason,
                extra={"honest_gap": "heuristic, not AI-driven shadow detection"},
            )
        )
    if store is not None:
        for shadow in shadows:
            store.insert(
                "findings_shadow",
                {
                    "location": shadow.location,
                    "kind": shadow.kind,
                    "reason": shadow.reason,
                    "extra": shadow.extra,
                    "checked_at": utcnow(),
                },
            )
    return shadows
