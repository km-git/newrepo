"""JSON by default; ``--human`` renders a Rich table for list-of-dict payloads."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def to_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n"


def emit(payload: object, *, human: bool = False) -> str:
    if not human:
        return to_json(payload)
    rows: list[dict[str, Any]]
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        rows = [r for r in payload["rows"] if isinstance(r, dict)]
        if not rows:
            return to_json(payload)
    else:
        return to_json(payload)
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    table = Table(show_header=True)
    for col in columns:
        table.add_column(str(col))
    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in columns])
    console = Console(record=True, width=120)
    console.print(table)
    return console.export_text()
