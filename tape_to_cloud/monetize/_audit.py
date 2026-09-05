"""Append-only audit log for the monetize store.

Every mutating operation in the monetize module appends one JSONL line
(who / what / when / hash) per the blueprint's audit-first posture
(section 5: integrity and chain of custody).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_LOG_FILENAME = "audit_log.jsonl"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization (sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def default_actor() -> str:
    return os.environ.get("TTC_ACTOR") or os.environ.get("USER") or "unknown"


def append_audit(
    store_dir: Path,
    action: str,
    detail: dict[str, Any],
    actor: str | None = None,
) -> dict[str, Any]:
    """Append an audit entry and return it (including its content hash)."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "ts": utc_now_iso(),
        "actor": actor or default_actor(),
        "action": action,
        "detail": detail,
    }
    entry["sha256"] = sha256_hex(canonical_json(entry))
    with (store_dir / AUDIT_LOG_FILENAME).open("a", encoding="utf-8") as fh:
        fh.write(canonical_json(entry) + "\n")
    return entry


def read_audit_log(store_dir: Path) -> list[dict[str, Any]]:
    path = Path(store_dir) / AUDIT_LOG_FILENAME
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries
