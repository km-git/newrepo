"""Shared JSON / human output helpers."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

_SECRET_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "client_secret",
        "authorization",
        "credential",
        "private_key",
        "access_key",
        "prompt",
    }
)
_SECRET_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credential",
    "authorization",
    "private_key",
)
_SECRET_VALUE_RE = re.compile(
    r"(?i)(?:"
    r"api[_ -]?key\s*[:=]\s*\S+|"
    r"bearer\s+[a-z0-9._-]{8,}|"
    r"ghp_[a-z0-9]{20,}|"
    r"sk-[a-z0-9]{8,}|"
    r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"
    r")"
)


def _is_secret_key(key: str) -> bool:
    low = str(key).lower()
    if low in _SECRET_KEYS:
        return True
    return any(fragment in low for fragment in _SECRET_KEY_FRAGMENTS)


def _redact_scalar(value: Any) -> Any:
    if isinstance(value, str) and _SECRET_VALUE_RE.search(value):
        return "[redacted]"
    return value


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: "[redacted]" if _is_secret_key(key) else _redact(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_redact(item) for item in obj]
    return _redact_scalar(obj)


def _safe_json(data: Any) -> str:
    return json.dumps(_redact(data), indent=2, default=str)


def emit(data: Any, human: bool = False, title: str = "DSPM") -> None:
    redacted = _redact(data)
    if human:
        _print_human(redacted, title)
    else:
        sys.stdout.write(_safe_json(redacted) + "\n")


def _print_human(data: Any, title: str) -> None:
    console = Console()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        table = Table(title=title)
        keys = list(data[0].keys())
        for key in keys:
            table.add_column(str(key))
        for row in data:
            table.add_row(*(str(_redact_scalar(row.get(k, ""))) for k in keys))
        console.print(table)
    elif isinstance(data, dict):
        table = Table(title=title)
        table.add_column("Key")
        table.add_column("Value")
        for k, v in data.items():
            display = "[redacted]" if _is_secret_key(str(k)) else str(_redact_scalar(v))
            table.add_row(str(k), display)
        console.print(table)
    else:
        console.print(_redact_scalar(data))
