"""Append-only chain-of-custody log (JSONL)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def append_event(log_path: Path, event: str, **fields: Any) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    seq = 0
    if log_path.is_file():
        seq = sum(1 for _ in log_path.open(encoding="utf-8") if _.strip())
    record = {
        "seq": seq + 1,
        "utc": datetime.now(UTC).isoformat(),
        "event": event,
        **fields,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
    return record


def load_events(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out
