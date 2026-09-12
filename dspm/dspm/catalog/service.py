"""Data catalog — Unity Catalog / Horizon / OpenMetadata inspired."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from dspm.store.db import fetch_all, init_db, insert_row

CLASSIFICATION_TAGS = ["PII", "PHI", "PCI", "RESTRICTED", "SENSITIVE", "INTERNAL", "PUBLIC"]


def register_asset(
    name: str,
    asset_type: str,
    owner: str = "data-team",
    tags: list[str] | None = None,
    lineage_parent: str | None = None,
) -> dict[str, Any]:
    init_db()
    urn = f"urn:dspm:asset:{asset_type}:{name.replace(' ', '_').lower()}"
    existing = [a for a in fetch_all("catalog_assets", limit=500) if a.get("urn") == urn]
    if existing:
        return existing[0]
    row = {
        "urn": urn,
        "name": name,
        "asset_type": asset_type,
        "owner": owner,
        "tags": json.dumps(tags or []),
        "lineage_parent": lineage_parent or "",
        "created_at": datetime.now(UTC).isoformat(),
    }
    insert_row("catalog_assets", row)
    return {"urn": urn, **row}


def build_lineage_graph() -> dict[str, Any]:
    assets = fetch_all("catalog_assets", limit=500)
    nodes = [{"id": a["urn"], "label": a["name"], "type": a["asset_type"]} for a in assets]
    edges = [{"from": a["lineage_parent"], "to": a["urn"]} for a in assets if a.get("lineage_parent")]
    return {"nodes": nodes, "edges": edges, "tag_taxonomy": CLASSIFICATION_TAGS}


def sync_from_discovery(stores: list[dict]) -> list[dict]:
    registered = []
    for s in stores:
        asset = register_asset(
            name=s.get("location", "unknown"),
            asset_type=s.get("store_type", "dataset"),
            tags=["INTERNAL"],
            lineage_parent=f"urn:dspm:source:{s.get('provider', 'on-prem')}",
        )
        registered.append(asset)
    return registered
