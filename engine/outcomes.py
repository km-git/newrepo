"""Outcome-driven trade setups: scalp, day, swing, long-term."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from core.atr import compute_atr14
from core.indicators import score_indicator_confluence
from core.risk import MAX_STOP_PCT, build_dca_ladder, dynamic_stop, dynamic_targets, risk_package
from engine.indicator_calibration import load_calibration, score_indicator_confluence_calibrated
from engine.readiness import resolve_execution_status
from engine.tv_edge import merge_tv_tokens_into_indicators

STYLE_CONFIG = {
  "scalp": {
    "primary_tf": "15m",
    "context_tfs": ["15m", "1h"],
    "horizon": "15m–4h",
    "atr_mult_sl": 0.8,
    "account_risk_pct": 0.5,
    "min_rr": 1.2,
  },
  "day_trade": {
    "primary_tf": "1h",
    "context_tfs": ["1h", "4h"],
    "horizon": "4h–2d",
    "atr_mult_sl": 1.2,
    "account_risk_pct": 0.75,
    "min_rr": 1.3,
  },
  "swing": {
    "primary_tf": "1d",
    "context_tfs": ["1d", "4h"],
    "horizon": "2d–4w",
    "atr_mult_sl": 1.8,
    "account_risk_pct": 1.0,
    "min_rr": 1.5,
  },
  "long_term": {
    "primary_tf": "1w",
    "context_tfs": ["1w", "1d"],
    "horizon": "1w–6m",
    "atr_mult_sl": 2.5,
    "account_risk_pct": 1.5,
    "min_rr": 2.0,
  },
}


def _dir_norm(d: str) -> str:
  return "LONG" if d.upper() in ("BULL", "LONG") else "SHORT"


def _structure_low_high(mws: List[dict]) -> tuple[float, float]:
  if not mws:
    return 0.0, 0.0
  lows = [m["price_start"] for m in mws[-3:]] + [m["price_end"] for m in mws[-3:]]
  highs = lows[:]
  return min(lows), max(highs)


def build_style_setup(
  style: str,
  data: Dict[str, pd.DataFrame],
  adaptive: dict,
  wave_structure: dict,
  direction: str,
  kz_low: float,
  kz_high: float,
  harmonic_overlaps: List[dict],
  in_zone: bool,
  consensus: dict,
  c_targets: dict,
  executive: dict,
  market_tools: Optional[dict] = None,
  expert_direction: Optional[dict] = None,
  cycle_confluence: Optional[dict] = None,
  tv_edge: Optional[dict] = None,
) -> dict:
  cfg = STYLE_CONFIG[style]
  tf = cfg["primary_tf"]
  if tf not in data or tf not in adaptive:
    return {"style": style, "status": "not_actionable", "honest_reason": f"missing {tf} data"}

  df = data[tf]
  current = float(df["Close"].iloc[-1])
  atr = compute_atr14(df)
  wave = wave_structure.get(tf, {})
  mws = adaptive[tf]["monowaves"]
  s_low, s_high = _structure_low_high(mws)
  direction = _dir_norm(direction)
  consensus_dir = consensus.get("consensus_direction", "NEUTRAL")

  # Harmonic for this TF
  harm_tf = [h for h in harmonic_overlaps if h.get("tf") == tf]
  if not harm_tf:
    harm_tf = [h for h in harmonic_overlaps if h.get("near_price")][:1]
  prz = (harm_tf[0]["prz_low"], harm_tf[0]["prz_high"]) if harm_tf else None

  entry_anchor = current if in_zone else (kz_low + kz_high) / 2
  fibs = [kz_low, kz_high] if kz_low < kz_high else []

  dca = build_dca_ladder(direction, entry_anchor, atr, kz_low, kz_high, fibs)
  max_sl = MAX_STOP_PCT.get(style, 8.0)
  stop = dynamic_stop(
    direction, entry_anchor, atr, s_low, s_high, cfg["atr_mult_sl"], max_stop_pct=max_sl
  )
  targets = dynamic_targets(
    direction,
    entry_anchor,
    atr,
    prz,
    c_targets.get("c_target_100"),
    c_targets.get("c_target_161"),
  )
  if stop.get("capped"):
    risk_unit = abs(entry_anchor - stop["price"])
    if risk_unit > 0:
      for t in targets:
        t["rr"] = round(abs(float(t["price"]) - entry_anchor) / risk_unit, 2)
  rr = targets[1]["rr"] if len(targets) > 1 else 0
  harmonic_near = bool(harm_tf)
  calibration = load_calibration()
  if calibration and calibration.get("available"):
    indicators = score_indicator_confluence_calibrated(
      df, direction, kz_low, kz_high, style, calibration
    )
  else:
    indicators = score_indicator_confluence(df, direction, kz_low, kz_high, style)
  indicators["stop_dist_pct"] = stop.get("distance_pct")
  if tv_edge or mkt:
    indicators = merge_tv_tokens_into_indicators(indicators, tv_edge or {}, mkt)
  mkt = market_tools or {}
  # Calibrated scoring uses ledger-validated tokens only — no expert/cycle inflation
  boost = 0 if indicators.get("calibrated") else mkt.get("confluence_boost", 0)
  if not indicators.get("calibrated") and expert_direction:
    boost += min(8, int(expert_direction.get("confidence", 0) * 10))
  if not indicators.get("calibrated") and cycle_confluence:
    cy = cycle_confluence.get("cycle_direction", "NEUTRAL")
    dir_bull = direction == "LONG"
    cy_bull = cy == "BULL"
    if (dir_bull and cy_bull) or (not dir_bull and cy == "BEAR"):
      boost += min(6, cycle_confluence.get("confluence_boost", 0) // 3)
  if boost:
    indicators["score"] = min(100, indicators["score"] + boost)
    indicators["aligned"] = indicators["score"] >= indicators.get("threshold", 58)
    indicators["signals"] = list(indicators.get("signals", [])) + mkt.get("confluence_signals", [])[:2]
  if not indicators.get("calibrated") and expert_direction and expert_direction.get("confluence_signals"):
    indicators["signals"] = list(indicators.get("signals", [])) + expert_direction["confluence_signals"][:2]
  status, execution_tier, reason = resolve_execution_status(
    style=style,
    direction=direction,
    wave=wave,
    in_zone=in_zone,
    zone_dist_pct=indicators.get("zone_dist_pct", 99.0),
    impulse_valid=wave.get("impulse_valid", False),
    consensus_dir=consensus_dir,
    rr=rr,
    min_rr=cfg["min_rr"],
    harmonic_near=harmonic_near,
    indicator=indicators,
    executive_verdict=executive.get("verdict", ""),
    expert_confidence=expert_direction.get("confidence", 0) if expert_direction else 0,
    cycle_aligned=(
      cycle_confluence is not None
      and cycle_confluence.get("cycle_direction") in (
        direction, "BULL" if direction == "LONG" else "BEAR"
      )
    ),
    oos_win_rate=None,
    oos_trades=0,
    impulse_partial=wave.get("impulse_partial", False),
    smc_valid=bool(tv_edge.get("smc_valid")) if tv_edge else False,
    smc_partial=bool(tv_edge.get("smc_partial")) if tv_edge else False,
    smc_aligned=bool(tv_edge.get("smc_aligned")) if tv_edge else False,
    smc_structure=tv_edge.get("smc_structure", "") if tv_edge else "",
  )

  probe_size_pct = 50 if execution_tier == "probe" else 100
  risk = risk_package(entry_anchor, stop["price"], cfg["account_risk_pct"] * probe_size_pct / 100)

  return {
    "style": style,
    "timeframe": tf,
    "horizon": cfg["horizon"],
    "status": status,
    "execution_tier": execution_tier,
    "readiness_score": indicators.get("score", 0),
    "indicator_signals": indicators.get("signals", []),
    "zone_dist_pct": indicators.get("zone_dist_pct"),
    "direction": direction,
    "honest_reason": reason,
    "wave_structure": wave.get("structure"),
    "wave_valid": wave.get("impulse_valid", False),
    "wave_partial": wave.get("impulse_partial", False),
    "smc_valid": bool(tv_edge.get("smc_valid")) if tv_edge else False,
    "smc_partial": bool(tv_edge.get("smc_partial")) if tv_edge else False,
    "smc_structure": tv_edge.get("smc_structure") if tv_edge else None,
    "tv_edge_score": tv_edge.get("edge_score") if tv_edge else None,
    "violations": wave.get("violations", [])[:2],
    "entry": {
      "anchor": round(entry_anchor, 6),
      "zone": [round(kz_low, 6), round(kz_high, 6)],
      "order_type": (
        "market"
        if status == "executable" and in_zone and execution_tier == "full"
        else "limit"
      ),
    },
    "dca": dca,
    "stop_loss": stop,
    "targets": targets,
    "risk": risk,
    "indicators": indicators,
    "market_tools": {
      "boost": boost,
      "signals": mkt.get("confluence_signals", [])[:3],
      "calibration_tokens": mkt.get("calibration_tokens", []),
      "orderbook": mkt.get("orderbook", {}).get("available"),
      "funding": mkt.get("funding", {}).get("available"),
      "rsi_stack": mkt.get("multi_tf_rsi", {}).get("bias"),
      "btc_corr": mkt.get("btc_correlation", {}).get("correlation"),
    },
    "expert_direction": expert_direction,
    "cycle_confluence": {
      "direction": (cycle_confluence or {}).get("cycle_direction"),
      "hurst": (cycle_confluence or {}).get("primary_hurst"),
      "phase": (cycle_confluence or {}).get("primary_phase"),
    } if cycle_confluence else None,
    "harmonic": harm_tf[0] if harm_tf else None,
    "monitor": {
      "check_interval": tf,
      "invalidate_if": [
        f"1d close beyond stop {stop['price']}",
        f"{tf} impulse flips opposite",
        "readiness_score drops below 40",
      ],
      "upgrade_if": [
        f"{tf} impulse passes R1/R2/R3",
        "price enters entry zone with rejection wick",
        f"readiness_score >= {indicators.get('threshold', 58)}",
      ],
    },
  }


def build_outcomes(
  symbol: str,
  data: Dict[str, pd.DataFrame],
  adaptive: dict,
  wave_structure: dict,
  direction: str,
  kz_low: float,
  kz_high: float,
  harmonic_overlaps: List[dict],
  in_zone: bool,
  consensus: dict,
  c_targets: dict,
  executive: dict,
  market_tools: Optional[dict] = None,
  expert_direction: Optional[dict] = None,
  cycle_confluence: Optional[dict] = None,
  tv_edge: Optional[dict] = None,
) -> dict:
  mkt = market_tools or {}
  boost = mkt.get("confluence_boost", 0)
  setups = {}
  for style in STYLE_CONFIG:
    setups[style] = build_style_setup(
      style, data, adaptive, wave_structure, direction,
      kz_low, kz_high, harmonic_overlaps, in_zone, consensus, c_targets, executive,
      market_tools=mkt,
      expert_direction=expert_direction,
      cycle_confluence=cycle_confluence,
      tv_edge=tv_edge,
    )

  executable = [s for s in setups.values() if s.get("status") == "executable"]
  full_exec = [s for s in executable if s.get("execution_tier") == "full"]
  probe_exec = [s for s in executable if s.get("execution_tier") == "probe"]
  monitor = [s for s in setups.values() if s.get("status") == "monitor"]
  skip = [s for s in setups.values() if s.get("status") == "not_actionable"]

  # Primary = best honest outcome
  if executable:
    primary = max(executable, key=lambda s: (s.get("readiness_score", 0), s["targets"][1]["rr"] if s.get("targets") else 0))
    primary_key = primary["style"]
    primary_status = "executable"
  elif monitor:
    primary = monitor[0]
    primary_key = primary["style"]
    primary_status = "monitor"
  else:
    primary = setups.get("swing", {})
    primary_key = "swing"
    primary_status = "not_actionable"

  return {
    "symbol": symbol,
    "honest_summary": {
      "primary_style": primary_key,
      "primary_status": primary_status,
      "primary_direction": primary.get("direction"),
      "executable_count": len(executable),
      "full_executable_count": len(full_exec),
      "probe_executable_count": len(probe_exec),
      "monitor_count": len(monitor),
      "not_actionable_count": len(skip),
      "executive_verdict": executive.get("verdict"),
      "expert_direction": expert_direction.get("direction") if expert_direction else None,
      "expert_confidence": expert_direction.get("confidence") if expert_direction else None,
      "cycle_direction": cycle_confluence.get("cycle_direction") if cycle_confluence else None,
      "truth": (
        f"{len(full_exec)} full + {len(probe_exec)} probe executable, "
        f"{len(monitor)} monitor, {len(skip)} skip — primary={primary_key} ({primary_status})"
      ),
    },
    "setups": setups,
  }
