"""JSON-default CLI output with optional human tables."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


def emit(payload: Any, *, human: bool = False) -> str:
    """Serialize *payload* as JSON, or a compact table when ``human`` is set."""
    if human:
        return render_human(payload)
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def render_human(payload: Any) -> str:
    if isinstance(payload, Mapping):
        rows = [dict(payload)]
        return _table(rows)
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        rows = [dict(item) if isinstance(item, Mapping) else {"value": item} for item in payload]
        return _table(rows)
    return str(payload)


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(empty)"
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(str(key))
    widths = {k: max(len(k), *(len(str(r.get(k, ""))) for r in rows)) for k in keys}
    header = "  ".join(k.ljust(widths[k]) for k in keys)
    rule = "  ".join("-" * widths[k] for k in keys)
    body = "\n".join("  ".join(str(r.get(k, "")).ljust(widths[k]) for k in keys) for r in rows)
    return f"{header}\n{rule}\n{body}"
