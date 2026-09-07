"""Shared JSON / human output helpers."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

_SECRET_KEYS = frozenset({"password", "secret", "token", "api_key", "client_secret", "authorization"})


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: "[redacted]" if str(key).lower() in _SECRET_KEYS else _redact(value)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(item) for item in obj]
    return obj


def emit(data: Any, human: bool = False, title: str = "DSPM") -> None:
    data = _redact(data)
    if human:
        _print_human(data, title)
    else:
        print(json.dumps(data, indent=2, default=str))


def _print_human(data: Any, title: str) -> None:
    console = Console()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        table = Table(title=title)
        keys = list(data[0].keys())
        for key in keys:
            table.add_column(str(key))
        for row in data:
            table.add_row(*(str(row.get(k, "")) for k in keys))
        console.print(table)
    elif isinstance(data, dict):
        table = Table(title=title)
        table.add_column("Key")
        table.add_column("Value")
        for k, v in data.items():
            table.add_row(str(k), str(v))
        console.print(table)
    else:
        console.print(data)
