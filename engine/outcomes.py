"""Outcome-driven trade setups: scalp, day, swing, long-term."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from core.atr import compute_atr14
from core.risk import build_dca_ladder, dynamic_stop, dynamic_targets, risk_package

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


def _honest_status(
  style: str,
  direction: str,
  wave: dict,
  in_zone: bool,
  impulse_valid: bool,
  consensus_dir: str,
  rr: float,
  min_rr: float,
  harmonic_near: bool,
) -> tuple[str, str]:
  """Returns (status, honest_reason). status: executable | monitor | not_actionable"""
  gaps: List[str] = []
  if wave.get("structure", "").startswith("invalid"):
    gaps.append(wave["structure"])
  if not impulse_valid and style in ("scalp", "day_trade"):
    gaps.append(f"{style} needs TF impulse confirmation")
  if consensus_dir not in ("NEUTRAL", direction, "BULL" if direction == "LONG" else "BEAR"):
    gaps.append(f"consensus={consensus_dir} vs {direction}")

  if rr < min_rr:
    return "not_actionable", f"R:R {rr:.2f} below min {min_rr} for {style}"

  if impulse_valid and in_zone and rr >= min_rr and not gaps:
    return "executable", f"{style} confluence: impulse valid, in zone, R:R {rr:.2f}"

  if harmonic_near or (in_zone and rr >= min_rr * 0.9):
    reason = f"Monitor {style}: " + ("harmonic PRZ active" if harmonic_near else "in zone, await 15m/1h close")
    if gaps:
      reason += f" (gaps: {'; '.join(gaps[:2])})"
    return "monitor", reason

  if gaps:
    return "monitor", f"Conditional {style}: {'; '.join(gaps[:3])}"

  return "not_actionable", f"No {style} edge: structure={wave.get('structure', 'n/a')}, R:R={rr:.2f}"


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
  stop = dynamic_stop(direction, entry_anchor, atr, s_low, s_high, cfg["atr_mult_sl"])
  targets = dynamic_targets(
    direction,
    entry_anchor,
    atr,
    prz,
    c_targets.get("c_target_100"),
    c_targets.get("c_target_161"),
  )
  rr = targets[1]["rr"] if len(targets) > 1 else 0
  status, reason = _honest_status(
    style,
    direction,
    wave,
    in_zone,
    wave.get("impulse_valid", False),
    consensus_dir,
    rr,
    cfg["min_rr"],
    bool(harm_tf),
  )

  risk = risk_package(entry_anchor, stop["price"], cfg["account_risk_pct"])

  return {
    "style": style,
    "timeframe": tf,
    "horizon": cfg["horizon"],
    "status": status,
    "direction": direction,
    "honest_reason": reason,
    "wave_structure": wave.get("structure"),
    "wave_valid": wave.get("impulse_valid", False),
    "violations": wave.get("violations", [])[:2],
    "entry": {
      "anchor": round(entry_anchor, 6),
      "zone": [round(kz_low, 6), round(kz_high, 6)],
      "order_type": "market" if status == "executable" and in_zone else "limit",
    },
    "dca": dca,
    "stop_loss": stop,
    "targets": targets,
    "risk": risk,
    "harmonic": harm_tf[0] if harm_tf else None,
    "monitor": {
      "check_interval": tf,
      "invalidate_if": [
        f"1d close beyond stop {stop['price']}",
        f"{tf} impulse flips opposite",
      ],
      "upgrade_if": [
        f"{tf} impulse passes R1/R2/R3",
        "price enters entry zone with rejection wick",
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
) -> dict:
  setups = {}
  for style in STYLE_CONFIG:
    setups[style] = build_style_setup(
      style, data, adaptive, wave_structure, direction,
      kz_low, kz_high, harmonic_overlaps, in_zone, consensus, c_targets,
    )

  executable = [s for s in setups.values() if s.get("status") == "executable"]
  monitor = [s for s in setups.values() if s.get("status") == "monitor"]
  skip = [s for s in setups.values() if s.get("status") == "not_actionable"]

  # Primary = best honest outcome
  if executable:
    primary = max(executable, key=lambda s: s["targets"][1]["rr"] if s.get("targets") else 0)
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
      "monitor_count": len(monitor),
      "not_actionable_count": len(skip),
      "executive_verdict": executive.get("verdict"),
      "truth": (
        f"{len(executable)} executable, {len(monitor)} monitor, {len(skip)} skip — "
        f"primary={primary_key} ({primary_status})"
      ),
    },
    "setups": setups,
  }
