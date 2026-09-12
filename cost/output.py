"""JSON-first CLI output with optional Rich tables."""

from __future__ import annotations

import json
from typing import Any


def emit(payload: Any, *, human: bool = False) -> str:
    if not human:
        return json.dumps(payload, indent=2, sort_keys=True, default=str)
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console(record=True)
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            table = Table(show_header=True)
            for key in payload[0]:
                table.add_column(str(key))
            for row in payload:
                table.add_row(*[str(row.get(k, "")) for k in payload[0]])
            console.print(table)
            return console.export_text()
        console.print(payload)
        return console.export_text()
    except Exception:
        return json.dumps(payload, indent=2, default=str)
