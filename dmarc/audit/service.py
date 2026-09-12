"""Write dmarc-inventory.json and ensure the findings store exists."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dmarc.audit.models import build_inventory
from dmarc.paths import inventory_path, output_dir
from dmarc.store import connect, dump_json


def run_inventory(root: Path | None = None) -> dict[str, Any]:
    """Create the SQLite schema and write the OSS inventory artifact."""
    output_dir(root)
    connect(root)  # auto-creates the six findings tables
    payload = build_inventory()
    dest = inventory_path(root)
    dump_json(dest.name, payload, root)
    payload["path"] = str(dest)
    return payload
