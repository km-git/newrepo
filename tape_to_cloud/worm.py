"""Local WORM lock: refuse unlink/overwrite of locked objects."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class WormLockedError(PermissionError):
    """Object is under COMPLIANCE retention lock."""


def lock_path(job_dir: Path) -> Path:
    return job_dir / "worm.json"


def apply_lock(job_dir: Path, *, until_utc: str, mode: str = "COMPLIANCE") -> dict[str, Any]:
    payload = {
        "mode": mode,
        "locked": True,
        "lock_until": until_utc,
        "applied_utc": datetime.now(UTC).isoformat(),
    }
    path = lock_path(job_dir)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def load_lock(job_dir: Path) -> dict[str, Any] | None:
    path = lock_path(job_dir)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def assert_unlocked(job_dir: Path) -> None:
    lock = load_lock(job_dir)
    if not lock or not lock.get("locked"):
        return
    until = str(lock.get("lock_until") or "")
    if until:
        try:
            expiry = datetime.fromisoformat(until.replace("Z", "+00:00"))
            if datetime.now(UTC) >= expiry:
                return
        except ValueError:
            pass
    raise WormLockedError(f"WORM {lock.get('mode')} lock until {until or 'indefinite'}")
