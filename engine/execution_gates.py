"""Pre-execution gates — honesty, macro, risk, intel."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple


def execution_gates_enabled() -> bool:
  return os.environ.get("EW_EXECUTION_GATES", "1").lower() not in ("0", "false", "no")


def gate_row(row: dict, *, intel: Optional[dict] = None) -> Tuple[bool, List[str]]:
  """
  Returns (allowed, reasons).
  Never bypasses honest gates — only adds macro/risk/intel blocks.
  """
  reasons: List[str] = []
  if not execution_gates_enabled():
    return True, reasons

  if row.get("row_type") == "contingent_scenario":
    reasons.append("contingent_scenario_requires_trigger")
    return False, reasons

  if row.get("gtc_tier") != "executable":
    reasons.append(f"gtc_tier={row.get('gtc_tier')}")
    return False, reasons

  if row.get("macro_mode") == "NUKE":
    reasons.append("macro_nuke_cancel_longs")
    return False, reasons

  if row.get("hist_action") == "downgrade":
    reasons.append("autodream_downgrade")
    return False, reasons

  cap = row.get("gtc_size_cap_pct", 100)
  if cap is not None and float(cap) <= 0:
    reasons.append("size_cap_zero")
    return False, reasons

  verdict = str(row.get("executive_verdict", ""))
  blocked = os.environ.get("EW_BLOCK_VERDICTS", "REJECT").split(",")
  if verdict in [b.strip() for b in blocked if b.strip()]:
    reasons.append(f"verdict_blocked={verdict}")
    return False, reasons

  intel = intel or {}
  fg = (intel.get("web_intel") or {}).get("fear_greed") or {}
  if fg.get("available") and fg.get("value", 50) <= 10:
    if row.get("direction") == "LONG" and os.environ.get("EW_BLOCK_LONG_EXTREME_FEAR", "0") == "1":
      reasons.append("extreme_fear_long_blocked")
      return False, reasons

  ws = intel.get("ws") or {}
  if ws.get("age_sec") is not None and ws["age_sec"] > float(os.environ.get("EW_WS_MAX_AGE_SEC", "120")):
    reasons.append(f"stale_ws_{ws['age_sec']}s")
    # warn only — don't block by default

  return True, reasons
