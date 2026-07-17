"""Live fill tracking — reconcile broker fills with autodream tracked_setups."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


FILLS_PATH = Path(os.environ.get("EW_FILLS_LOG", "output/execution/live_fills.jsonl"))


def record_live_fill(fill: dict) -> None:
  FILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
  entry = dict(fill)
  entry["recorded_at"] = datetime.now(timezone.utc).isoformat()
  with FILLS_PATH.open("a") as f:
    f.write(json.dumps(entry, default=str) + "\n")


def load_fills(limit: int = 500) -> List[dict]:
  if not FILLS_PATH.exists():
    return []
  rows = []
  for line in FILLS_PATH.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line:
      try:
        rows.append(json.loads(line))
      except json.JSONDecodeError:
        continue
  return rows[-limit:]


def reconcile_fill_to_setup(fill: dict) -> Optional[dict]:
  """Match client_id to tracked setup id pattern."""
  cid = fill.get("client_id") or fill.get("order_id", "")
  if not cid or not cid.startswith("ew-"):
    return None
  parts = cid.split("-")
  if len(parts) < 3:
    return None
  return {"client_id": cid, "fill": fill, "matched": True}
