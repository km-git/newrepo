"""Shared honesty gates for executable labeling and executive board."""

from __future__ import annotations

from typing import List, Tuple

from engine.accurate_setups import MIN_OOS_TRADES, _stop_ok


def setup_geometry_ok(setup: dict) -> Tuple[bool, str]:
  direction = (setup.get("direction") or "").upper()
  entry = float((setup.get("entry") or {}).get("anchor") or 0)
  sl = float((setup.get("stop_loss") or {}).get("price") or 0)
  tgs = setup.get("targets") or []
  tps = [float(t.get("price") or 0) for t in tgs[:3]]
  if entry <= 0 or sl <= 0 or any(p <= 0 for p in tps if p):
    return False, "non_positive_price"
  if direction in ("LONG", "BULL"):
    if not (sl < entry < tps[0] < (tps[1] if len(tps) > 1 else tps[0])):
      return False, "long_geometry"
  else:
    if not (sl > entry > tps[0] > (tps[1] if len(tps) > 1 else tps[0])):
      return False, "short_geometry"
  return True, "ok"


def is_honesty_executable(setup: dict, style: str) -> bool:
  if not setup or setup.get("status") != "executable":
    return False
  if not _stop_ok(setup, style):
    return False
  geom_ok, _ = setup_geometry_ok(setup)
  if not geom_ok:
    return False
  oos_n = int(setup.get("oos_trades") or 0)
  oos_wr = setup.get("oos_win_rate")
  if setup.get("oos_gate") != "passed":
    return False
  if oos_n < MIN_OOS_TRADES or oos_wr is None:
    return False
  return True
