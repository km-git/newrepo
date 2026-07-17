"""Live fill tracking — reconcile broker fills with autodream tracked_setups."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.broker.symbol_map import canonical_symbol


FILLS_PATH = Path(os.environ.get("EW_FILLS_LOG", "output/execution/live_fills.jsonl"))
_RECONCILED_PATH = Path(os.environ.get("EW_FILLS_RECONCILED", "output/execution/reconciled_fills.json"))


def _compact_symbol(symbol: str) -> str:
  return re.sub(r"[^A-Z0-9]", "", canonical_symbol(symbol).replace("/", ""))[:8]


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


def parse_client_id(client_id: str) -> Optional[Dict[str, Any]]:
  """Parse ew-{sym}-{tf}-L{n}[-suffix] into match keys."""
  cid = (client_id or "").strip()
  if not cid.startswith("ew-"):
    return None
  parts = cid.split("-")
  if len(parts) < 4:
    return None
  sym_compact = parts[1]
  tf = parts[2].lower()
  tail = "-".join(parts[3:]).lower()
  role = "entry"
  outcome = None
  if tail.endswith("sl") or "-sl" in tail:
    role = "stop"
    outcome = "sl_hit"
  elif "-tp" in tail:
    role = "take_profit"
    outcome = "tp1_hit"
  return {
    "client_id": cid,
    "sym_compact": sym_compact,
    "timeframe": tf,
    "role": role,
    "outcome": outcome,
  }


def reconcile_fill_to_setup(fill: dict, open_setups: Optional[List[dict]] = None) -> Optional[dict]:
  """Match fill client_id to an open tracked setup."""
  cid = fill.get("client_id") or fill.get("order_id", "")
  parsed = parse_client_id(str(cid))
  if not parsed:
    return None
  if open_setups is None:
    from engine.outcome_tracker import _load_state

    open_setups = _load_state().get("open", [])
  for setup in open_setups:
    if _compact_symbol(setup.get("symbol", "")) != parsed["sym_compact"]:
      continue
    setup_tf = str(setup.get("timeframe", "")).lower()
    if not setup_tf.startswith(parsed["timeframe"]) and parsed["timeframe"] not in setup_tf:
      continue
    return {
      "setup_id": setup.get("id"),
      "client_id": cid,
      "fill": fill,
      "parsed": parsed,
      "matched": True,
    }
  return None


def _load_reconciled_ids() -> set:
  if not _RECONCILED_PATH.exists():
    return set()
  try:
    data = json.loads(_RECONCILED_PATH.read_text(encoding="utf-8"))
    return set(data.get("client_ids", []))
  except (json.JSONDecodeError, OSError):
    return set()


def _save_reconciled_ids(ids: set) -> None:
  _RECONCILED_PATH.parent.mkdir(parents=True, exist_ok=True)
  _RECONCILED_PATH.write_text(
    json.dumps({"client_ids": sorted(ids), "updated": datetime.now(timezone.utc).isoformat()}, indent=2),
    encoding="utf-8",
  )


def reconcile_live_fills(*, open_setups: Optional[List[dict]] = None) -> List[Dict[str, Any]]:
  """
  Return fill→setup matches not yet reconciled.
  Stop/TP fills carry an outcome hint for outcome_tracker.
  """
  if open_setups is None:
    from engine.outcome_tracker import _load_state

    open_setups = _load_state().get("open", [])

  seen = _load_reconciled_ids()
  matches: List[Dict[str, Any]] = []
  for fill in load_fills():
    cid = str(fill.get("client_id") or fill.get("order_id") or "")
    if not cid or cid in seen:
      continue
    match = reconcile_fill_to_setup(fill, open_setups=open_setups)
    if match:
      matches.append(match)
      seen.add(cid)
  if matches:
    _save_reconciled_ids(seen)
  return matches
