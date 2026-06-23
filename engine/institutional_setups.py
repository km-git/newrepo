"""SMC institutional setup type — Sweep + OB + FVG on 15m/1h."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from core.atr import compute_atr14
from core.institutional_edge import build_institutional_matrix
from core.risk import MAX_STOP_PCT, dynamic_stop, dynamic_targets, risk_package
from engine.indicator_calibration import apply_extra_calibration_tokens, load_calibration
from engine.readiness import resolve_execution_status


SMC_STYLE = {
  "setup_type": "smc",
  "primary_tf": "15m",
  "context_tf": "1h",
  "timeframes": ["15m", "1h"],
  "horizon": "15m–4h",
  "atr_mult_sl": 1.0,
  "account_risk_pct": 0.75,
  "min_rr": 1.5,
}


def _dir_norm(d: str) -> str:
  if d in ("BULL", "LONG"):
    return "LONG"
  if d in ("BEAR", "SHORT"):
    return "SHORT"
  return d


def build_smc_setup(
  symbol: str,
  data: Dict[str, pd.DataFrame],
  direction: str,
  kz_low: float,
  kz_high: float,
  in_zone: bool,
  consensus: dict,
  executive: dict,
  institutional: Optional[dict] = None,
  exchange=None,
  market_tools: Optional[dict] = None,
) -> dict:
  """
  New setup type: institutional SMC entry (Phase 1–5).
  Entry signal: liquidity sweep + order block + FVG on 15m or 1h.
  """
  direction = _dir_norm(direction)
  tf = SMC_STYLE["primary_tf"]
  ctx_tf = SMC_STYLE["context_tf"]

  if tf not in data or len(data[tf]) < 40:
    return {
      "setup_type": "smc",
      "style": "smc",
      "status": "not_actionable",
      "honest_reason": f"missing {tf} data for SMC setup",
    }

  inst = institutional or build_institutional_matrix(
    data, direction, tfs=["15m", "1h", "4h"], exchange=exchange, symbol=symbol,
  )
  entry_tf = inst.get("best_entry_tf") or tf
  tf_analysis = inst.get("by_tf", {}).get(entry_tf, {})
  df = data[entry_tf]
  current = float(df["Close"].iloc[-1])
  atr = compute_atr14(df)

  # Entry anchor: OB mid > FVG mid > kill zone > current
  entry_anchor = current
  ob = tf_analysis.get("active_ob")
  fvg = tf_analysis.get("active_fvg")
  if ob:
    entry_anchor = (ob["top"] + ob["bot"]) / 2
  elif fvg:
    entry_anchor = (fvg["top"] + fvg["bot"]) / 2
  elif in_zone:
    entry_anchor = (kz_low + kz_high) / 2

  lo = float(df["Low"].iloc[-20:].min())
  hi = float(df["High"].iloc[-20:].max())
  stop = dynamic_stop(
    direction,
    entry_anchor,
    atr,
    lo,
    hi,
    SMC_STYLE["atr_mult_sl"],
    max_stop_pct=MAX_STOP_PCT.get("smc", 4.0),
  )
  targets = dynamic_targets(direction, entry_anchor, atr, None, None, None)
  if stop.get("capped"):
    risk_unit = abs(entry_anchor - stop["price"])
    if risk_unit > 0:
      for t in targets:
        t["rr"] = round(abs(float(t["price"]) - entry_anchor) / risk_unit, 2)
  rr = targets[1]["rr"] if len(targets) > 1 else 0

  score = int(inst.get("institutional_score", 0))
  tags = list(inst.get("tags", []))
  calibration = load_calibration()
  indicators = {
    "score": score,
    "threshold": 45,
    "aligned": score >= 45,
    "signals": tags[:6],
    "active_tokens": tags[:8],
    "zone_dist_pct": 0 if in_zone else 99,
    "stop_dist_pct": stop.get("distance_pct"),
    "calibrated": bool(calibration and calibration.get("available")),
  }
  mkt = market_tools or {}
  indicators = apply_extra_calibration_tokens(indicators, tags + mkt.get("calibration_tokens", []))

  entry_signal = inst.get("entry_signal", False)
  entry_grade = inst.get("entry_grade", "D")
  vp_ok = inst.get("vp_filter_ok", True)
  exec_ok = executive.get("verdict", "") in ("GO", "CONDITIONAL_GO", "STAGED_GO", "STANDBY_ORDERS")

  # SMC-specific execution resolution
  if entry_signal and vp_ok and rr >= SMC_STYLE["min_rr"] and indicators["aligned"]:
    status, tier, reason = "executable", "full", (
      f"SMC FULL: sweep+OB+FVG on {entry_tf}, grade {entry_grade}, R:R {rr:.2f}"
    )
  elif entry_grade in ("A", "B") and inst.get("confluence_count", 0) >= 2 and rr >= SMC_STYLE["min_rr"] * 0.9:
    status, tier, reason = "executable", "probe", (
      f"SMC PROBE: {inst.get('confluence_count')}/3 confluence on {entry_tf}, "
      f"grade {entry_grade}, score {score}/100"
    )
  elif score >= 35 and exec_ok:
    status, tier, reason = "monitor", "none", (
      f"Monitor SMC: {', '.join(tags[:3])} — await sweep+OB+FVG"
    )
  else:
    status, tier, reason = "not_actionable", "none", (
      f"No SMC edge: grade={entry_grade}, confluence={inst.get('confluence_count', 0)}/3, score={score}"
    )

  # Also allow EW readiness path as secondary check for probe demotion
  wave_stub = {
    "structure": tf_analysis.get("structure_event") or "smc",
    "impulse_valid": entry_signal,
    "impulse_partial": inst.get("confluence_count", 0) >= 2,
  }
  ew_status, ew_tier, _ = resolve_execution_status(
    style="day_trade",
    direction=direction,
    wave=wave_stub,
    in_zone=in_zone or bool(ob or fvg),
    zone_dist_pct=indicators.get("zone_dist_pct", 99),
    impulse_valid=entry_signal,
    consensus_dir=consensus.get("consensus_direction", "NEUTRAL"),
    rr=rr,
    min_rr=SMC_STYLE["min_rr"],
    harmonic_near=False,
    indicator=indicators,
    executive_verdict=executive.get("verdict", ""),
    impulse_partial=inst.get("confluence_count", 0) >= 2,
    smc_valid=entry_signal or entry_grade == "A",
    smc_partial=inst.get("confluence_count", 0) >= 1,
    smc_aligned=True,
    smc_structure=tf_analysis.get("structure_event", ""),
  )
  if ew_status == "executable" and status != "executable":
    status, tier = ew_status, ew_tier
    reason = f"SMC+EW: {reason}"

  probe_size = 50 if tier == "probe" else 100
  risk = risk_package(entry_anchor, stop["price"], SMC_STYLE["account_risk_pct"] * probe_size / 100)

  return {
    "setup_type": "smc",
    "style": "smc",
    "timeframe": entry_tf,
    "context_timeframe": ctx_tf,
    "horizon": SMC_STYLE["horizon"],
    "status": status,
    "execution_tier": tier,
    "readiness_score": indicators["score"],
    "indicator_signals": indicators["signals"],
    "direction": direction,
    "honest_reason": reason,
    "entry_signal": entry_signal,
    "entry_grade": entry_grade,
    "institutional_score": score,
    "confluence_count": inst.get("confluence_count", 0),
    "smc_source": tf_analysis.get("smc_source"),
    "structure_event": tf_analysis.get("structure_event"),
    "cvd_divergence": tf_analysis.get("cvd_divergence"),
    "volume_profile": tf_analysis.get("volume_profile"),
    "vp_filter_ok": vp_ok,
    "obi": tf_analysis.get("obi"),
    "ha_roc": tf_analysis.get("ha_roc"),
    "wave_valid": entry_signal,
    "wave_partial": inst.get("confluence_count", 0) >= 2,
    "smc_valid": entry_signal or entry_grade in ("A", "B"),
    "entry": {
      "anchor": round(entry_anchor, 6),
      "zone": [round(kz_low, 6), round(kz_high, 6)],
      "order_type": "limit",
    },
    "stop_loss": stop,
    "targets": targets,
    "risk": risk,
    "indicators": indicators,
    "institutional": inst,
    "monitor": {
      "check_interval": entry_tf,
      "upgrade_if": [
        "liquidity sweep + OB + FVG align",
        f"institutional score >= 55",
        "CVD divergence confirms direction",
      ],
    },
  }
