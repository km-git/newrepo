"""JSON / human table output helpers."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table


def emit(payload: Any, *, human: bool = False) -> str:
    if not human:
        return json.dumps(payload, indent=2, default=str)
    if isinstance(payload, dict):
        return _dict_table(payload)
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return _list_table(payload)
    return json.dumps(payload, indent=2, default=str)


def _dict_table(data: dict[str, Any]) -> str:
    table = Table(title="SSPM Result")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    for key, value in data.items():
        if isinstance(value, list | dict):
            value = json.dumps(value, default=str)[:120]
        table.add_row(str(key), str(value))
    console = Console(record=True, width=120)
    console.print(table)
    return console.export_text()


def _list_table(rows: list[dict[str, Any]]) -> str:
    keys = list(rows[0].keys())
    table = Table(title=f"SSPM Results ({len(rows)} rows)")
    for key in keys[:8]:
        table.add_column(str(key))
    for row in rows[:50]:
        table.add_row(*[str(row.get(k, ""))[:60] for k in keys[:8]])
    console = Console(record=True, width=140)
    console.print(table)
    return console.export_text()
