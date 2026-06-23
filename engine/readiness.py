"""Readiness scoring — path from monitor to executable."""

from __future__ import annotations

from typing import List, Optional, Tuple

from engine.indicator_calibration import MIN_OOS_EXECUTABLE, MIN_OOS_TRADES

# Executive verdicts that allow probe-tier execution
PROBE_VERDICTS = frozenset({"GO", "CONDITIONAL_GO", "STAGED_GO", "STANDBY_ORDERS"})

# Max distance from kill zone (%) to allow probe entry, by style
NEAR_ZONE_PCT = {"scalp": 2.5, "day_trade": 3.5, "swing": 6.0, "long_term": 10.0}
# STAGED_GO scale-in: allow wider approach if indicators strong
STAGED_ZONE_PCT = {"scalp": 5.0, "day_trade": 8.0, "swing": 12.0, "long_term": 15.0}


def _near_zone(
  style: str,
  in_zone: bool,
  zone_dist_pct: float,
  executive_verdict: str,
) -> bool:
  if in_zone:
    return True
  limit = NEAR_ZONE_PCT.get(style, 3.0)
  if executive_verdict == "STAGED_GO":
    limit = max(limit, STAGED_ZONE_PCT.get(style, limit))
  return zone_dist_pct < limit


def resolve_execution_status(
  style: str,
  direction: str,
  wave: dict,
  in_zone: bool,
  zone_dist_pct: float,
  impulse_valid: bool,
  consensus_dir: str,
  rr: float,
  min_rr: float,
  harmonic_near: bool,
  indicator: dict,
  executive_verdict: str,
  expert_confidence: float = 0.0,
  cycle_aligned: bool = False,
  oos_win_rate: Optional[float] = None,
  oos_trades: int = 0,
) -> Tuple[str, str, str]:
  """
  Returns (status, execution_tier, honest_reason).
  status: executable | monitor | not_actionable
  execution_tier: full | probe | none
  """
  gaps: List[str] = []
  structure = wave.get("structure", "")
  if structure.startswith("invalid"):
    gaps.append(structure)

  dir_bull = direction == "LONG"
  consensus_ok = consensus_dir in ("NEUTRAL", direction, "BULL" if dir_bull else "BEAR")
  if not consensus_ok:
    gaps.append(f"consensus={consensus_dir} vs {direction}")

  if rr < min_rr:
    return "not_actionable", "none", f"R:R {rr:.2f} below min {min_rr} for {style}"

  stop_dist = indicator.get("stop_dist_pct")
  max_stop = {"scalp": 2.5, "day_trade": 4.0, "swing": 8.0, "long_term": 12.0}.get(style, 4.0)
  if stop_dist is not None and float(stop_dist) > max_stop * 1.5:
    return (
      "monitor",
      "none",
      f"{style}: stop {float(stop_dist):.1f}% too wide (max {max_stop}%) — tighten or hedge before entry",
    )

  ind_score = indicator.get("score", 0)
  ind_aligned = indicator.get("aligned", False)
  # Expert + Hurst cycle stack can align probe when EW impulse is incomplete
  if expert_confidence >= 0.58 and cycle_aligned and not ind_aligned:
    ind_aligned = ind_score >= indicator.get("threshold", 58) - 8
  if expert_confidence >= 0.65 and cycle_aligned:
    ind_score = min(100, ind_score + 5)
  ind_signals = indicator.get("signals", [])
  near_zone = _near_zone(style, in_zone, zone_dist_pct, executive_verdict)
  exec_ok = executive_verdict in PROBE_VERDICTS

  def _oos_blocks_executable() -> Optional[str]:
    if oos_trades < MIN_OOS_TRADES or oos_win_rate is None:
      return None
    if float(oos_win_rate) < MIN_OOS_EXECUTABLE:
      return f"OOS gate: {float(oos_win_rate):.0%} < {MIN_OOS_EXECUTABLE:.0%}"
    return None

  # Tier 1: Full executable — strict EW + zone
  if impulse_valid and in_zone and rr >= min_rr and not gaps:
    oos_block = _oos_blocks_executable()
    if oos_block:
      return (
        "monitor",
        "none",
        f"{style} FULL blocked: impulse valid, in zone, R:R {rr:.2f} — {oos_block}",
      )
    return (
      "executable",
      "full",
      f"{style} FULL: impulse R1/R2/R3 valid, in zone, R:R {rr:.2f}",
    )

  # Tier 2: Probe — NO probe on invalid impulse; higher bar when out of zone
  probe_min_score = 72 if not in_zone else 65
  if structure.startswith("invalid"):
    gaps.append(structure)  # block probe on invalid structure

  if (
    ind_aligned
    and ind_score >= probe_min_score
    and near_zone
    and exec_ok
    and consensus_ok
    and rr >= min_rr
    and not any(g.startswith("invalid") for g in gaps)
    and (harmonic_near or in_zone or (expert_confidence >= 0.65 and cycle_aligned))
  ):
    missing = []
    if not impulse_valid:
      missing.append(f"{style} TF impulse pending")
    if not in_zone:
      missing.append(f"zone dist {zone_dist_pct:.1f}%")
    sig = ", ".join(ind_signals[:3])
    reason = (
      f"{style} PROBE executable: indicators {ind_score}/100 ({sig}) · "
      f"exec={executive_verdict} · R:R {rr:.2f}"
    )
    if expert_confidence >= 0.6 and cycle_aligned:
      reason += " · expert+Hurst aligned"
    if missing:
      reason += f" · use 25-50% probe — {'; '.join(missing)}"
    oos_block = _oos_blocks_executable()
    if oos_block:
      return (
        "monitor",
        "none",
        f"{style} PROBE blocked: {oos_block} · indicators {ind_score}/100",
      )
    return "executable", "probe", reason

  # Monitor paths
  if harmonic_near or (near_zone and rr >= min_rr * 0.9):
    reason = "Monitor " + style + ": "
    if harmonic_near:
      reason += "harmonic PRZ active"
    elif ind_aligned:
      reason += f"indicators {ind_score}/100 aligned, await impulse/zone"
    else:
      reason += "near zone, await 15m/1h close"
    if gaps:
      reason += f" (gaps: {'; '.join(gaps[:2])})"
    return "monitor", "none", reason

  if ind_aligned and ind_score >= 50:
    return (
      "monitor",
      "none",
      f"Conditional {style}: indicators {ind_score}/100 — {', '.join(ind_signals[:2])}"
      + (f"; {'; '.join(gaps[:2])}" if gaps else ""),
    )

  if gaps:
    return "monitor", "none", f"Conditional {style}: {'; '.join(gaps[:3])}"

  return (
    "not_actionable",
    "none",
    f"No {style} edge: structure={structure or 'n/a'}, indicators={ind_score}/100, R:R={rr:.2f}",
  )
