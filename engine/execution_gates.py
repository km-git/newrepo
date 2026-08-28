"""Pre-execution gates — honesty, macro, risk, intel."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set, Tuple


def execution_gates_enabled() -> bool:
  return os.environ.get("EW_EXECUTION_GATES", "1").lower() not in ("0", "false", "no")


def _normalize_direction(direction: str) -> str:
  d = str(direction or "").upper()
  if d in ("BULL",):
    return "LONG"
  if d in ("BEAR",):
    return "SHORT"
  return d


def blocked_timeframes() -> Set[str]:
  return {
    t.strip() for t in os.environ.get("EW_BLOCKED_TFS", "1d,12h").split(",") if t.strip()
  }


def allowed_directions() -> Optional[Set[str]]:
  """Explicit allow-list (LONG, SHORT). Empty env = no hard allow-list."""
  raw = os.environ.get("EW_ALLOWED_DIRECTIONS", "").strip()
  if not raw:
    return None
  out: Set[str] = set()
  for part in raw.split(","):
    d = _normalize_direction(part.strip())
    if d:
      out.add(d)
  return out or None


def blocked_directions(metrics: Optional[dict] = None) -> Set[str]:
  """
  Directions blocked by explicit env or historical underperformance.
  Data-driven: LONG at ~46% WR vs SHORT at ~62% — block weak side when n≥30.
  """
  explicit = {
    _normalize_direction(d.strip())
    for d in os.environ.get("EW_BLOCKED_DIRECTIONS", "").split(",")
    if d.strip()
  }
  if os.environ.get("EW_DIRECTION_GATES", "1").lower() in ("0", "false", "no"):
    return explicit

  try:
    if metrics is None:
      from engine.outcome_tracker import load_metrics

      metrics = load_metrics()
    th_wr = float(os.environ.get("EW_MIN_DIRECTION_WIN_RATE", "0.48"))
    th_n = float(os.environ.get("EW_MIN_DIRECTION_SAMPLES", "30"))
    by_dir = metrics.get("by_direction") or {}
    weak: Set[str] = set()
    for direction, bucket in by_dir.items():
      decided = int(bucket.get("decided") or 0)
      wr = bucket.get("win_rate")
      norm = _normalize_direction(direction)
      if decided >= th_n and wr is not None and wr < th_wr:
        weak.add(norm)
    return explicit | weak
  except Exception:
    return explicit


def direction_allowed(row: dict, metrics: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
  direction = _normalize_direction(row.get("direction", ""))
  if not direction:
    return False, "missing_direction"

  allow = allowed_directions()
  if allow is not None and direction not in allow:
    return False, f"direction_not_allowed_{direction}"

  blocked = blocked_directions(metrics)
  if direction in blocked:
    return False, f"direction_blocked_{direction}"
  return True, None


def filter_closed_for_policy(closed: List[dict], metrics: Optional[dict] = None) -> List[dict]:
  """Apply live execution policy to historical closed setups (walk-forward / audit)."""
  if metrics is None:
    try:
      from engine.outcome_tracker import load_metrics

      metrics = load_metrics()
    except Exception:
      metrics = {}

  blocked_tfs = blocked_timeframes()
  blocked_dirs = blocked_directions(metrics)
  regime_weak_tfs: Set[str] = set()
  if os.environ.get("EW_REGIME_GATES", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.effectiveness_gates import gate_thresholds

      th = gate_thresholds()
      for tf, bucket in (metrics.get("by_timeframe") or {}).items():
        if tf in blocked_tfs:
          continue
        decided = int(bucket.get("decided") or 0)
        wr = bucket.get("win_rate")
        if decided >= th["min_tf_samples"] and wr is not None and wr < th["min_tf_win_rate"]:
          regime_weak_tfs.add(tf)
    except Exception:
      pass

  out: List[dict] = []
  for s in closed:
    tf = str(s.get("timeframe") or "")
    if blocked_tfs and tf in blocked_tfs:
      continue
    if regime_weak_tfs and tf in regime_weak_tfs:
      continue
    direction = _normalize_direction(s.get("direction", ""))
    if blocked_dirs and direction in blocked_dirs:
      continue
    out.append(s)
  return out


def gate_row(row: dict, *, intel: Optional[dict] = None, portfolio_state=None) -> Tuple[bool, List[str]]:
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

  if str(row.get("timeframe") or "") in blocked_timeframes():
    reasons.append(f"tf_blocked={row.get('timeframe')}")
    return False, reasons

  dir_ok, dir_reason = direction_allowed(row)
  if not dir_ok and dir_reason:
    reasons.append(dir_reason)
    return False, reasons

  if row.get("honest_execution_tier") == "probe" and row.get("gtc_tier") == "monitor":
    reasons.append("monitor_probe_blocked")
    return False, reasons

  # Regime gate — block historically weak timeframes (effectiveness audit)
  if os.environ.get("EW_REGIME_GATES", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.effectiveness_gates import gate_thresholds
      from engine.outcome_tracker import load_metrics

      tf = str(row.get("timeframe") or "")
      bucket = (load_metrics().get("by_timeframe") or {}).get(tf) or {}
      decided = int(bucket.get("decided") or 0)
      wr = bucket.get("win_rate")
      th = gate_thresholds()
      if decided >= th["min_tf_samples"] and wr is not None and wr < th["min_tf_win_rate"]:
        reasons.append(f"regime_weak_tf_{tf}_wr_{wr:.0%}")
        return False, reasons
    except Exception:
      pass

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

  try:
    from engine.portfolio_risk import gate_portfolio_heat, portfolio_risk_enabled

    if portfolio_risk_enabled():
      allowed_heat, heat_reasons = gate_portfolio_heat(row, portfolio_state)
      if not allowed_heat:
        reasons.extend(heat_reasons)
        return False, reasons
  except Exception:
    pass

  return True, reasons
