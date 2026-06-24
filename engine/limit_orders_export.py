"""Pair × timeframe GTC limit order export — staged tiers without changing honest gates."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.risk import DCA_SPLITS, build_dca_ladder, dynamic_stop, dynamic_targets, risk_package

ALL_TIMEFRAMES = ("1w", "1d", "4h", "1h", "15m")

# Maps each TF to the style that owns honest executable gates (4h is context-only).
TF_STYLE_MAP = {
  "15m": "scalp",
  "1h": "day_trade",
  "4h": None,
  "1d": "swing",
  "1w": "long_term",
}

TF_CONFIG: Dict[str, dict] = {
  "15m": {
    "horizon": "15m–4h",
    "atr_mult_sl": 0.8,
    "account_risk_pct": 0.5,
    "min_rr": 1.2,
  },
  "1h": {
    "horizon": "4h–2d",
    "atr_mult_sl": 1.2,
    "account_risk_pct": 0.75,
    "min_rr": 1.3,
  },
  "4h": {
    "horizon": "4h–3d",
    "atr_mult_sl": 1.5,
    "account_risk_pct": 0.85,
    "min_rr": 1.4,
  },
  "1d": {
    "horizon": "2d–4w",
    "atr_mult_sl": 1.8,
    "account_risk_pct": 1.0,
    "min_rr": 1.5,
  },
  "1w": {
    "horizon": "1w–6m",
    "atr_mult_sl": 2.5,
    "account_risk_pct": 1.5,
    "min_rr": 2.0,
  },
}

TIER_RISK_MULT = {"executable": 1.0, "monitor": 0.5, "watch": 0.25}
TIER_SIZE_CAP = {"executable": 100, "monitor": 50, "watch": 25}


def _dir_norm(d: str) -> str:
  return "LONG" if str(d).upper() in ("BULL", "LONG") else "SHORT"


def _fib_levels_from_kz(kz: dict) -> Optional[List[float]]:
  """Extract numeric fib prices from kill-zone constituent_fibs dict."""
  raw = kz.get("constituent_fibs")
  if not raw:
    return None
  if isinstance(raw, dict):
    vals = [float(v) for v in raw.values() if v is not None]
  elif isinstance(raw, (list, tuple)):
    vals = [float(v) for v in raw if v is not None]
  else:
    return None
  return sorted(vals) if vals else None


def _c_targets(result: dict) -> dict:
  return result.get("step3_c_targets") or result.get("step3_kill_zone") or {}


def _normalize_results(batch_or_results: Any) -> List[dict]:
  if isinstance(batch_or_results, list):
    return batch_or_results
  if isinstance(batch_or_results, dict):
    for key in ("pairs", "results", "instruments"):
      if key in batch_or_results and isinstance(batch_or_results[key], list):
        return batch_or_results[key]
  raise TypeError("expected list of results or batch dict with pairs/results key")


def _structure_bounds(wave: dict, fallback_price: float, atr: float) -> Tuple[float, float]:
  """Derive structure low/high from recent monowaves when full adaptive data unavailable."""
  waves = wave.get("waves_last5") or []
  if waves:
    pts = []
    for w in waves[-3:]:
      pts.extend([float(w.get("start", 0)), float(w.get("end", 0))])
    return min(pts), max(pts)
  return fallback_price - 2 * atr, fallback_price + 2 * atr


def _harmonic_for_tf(result: dict, tf: str) -> Optional[dict]:
  for h in result.get("step4_harmonic_overlap") or []:
    if h.get("tf") == tf:
      return h
  return None


def _resolve_gtc_tier(result: dict, tf: str) -> Tuple[str, str, str]:
  """
  Map honest setup status → GTC tier without mutating step8 outcomes.
  Returns (gtc_tier, honest_execution_tier, tier_note).
  """
  style = TF_STYLE_MAP.get(tf)
  setups = (result.get("step8_outcomes") or {}).get("setups") or {}
  if style and style in setups:
    setup = setups[style]
    st = setup.get("status", "not_actionable")
    tier = setup.get("execution_tier", "none")
    reason = setup.get("honest_reason", "")
    if st == "executable":
      return "executable", tier, reason
    if st == "monitor":
      return "monitor", "none", reason
    return "watch", "none", reason or f"{style} not_actionable — staged GTC only"

  wave = (result.get("step2_wave_structure") or {}).get(tf) or {}
  if _harmonic_for_tf(result, tf):
    return "monitor", "none", f"{tf} harmonic PRZ — staged GTC monitor tier"
  if wave.get("impulse_valid"):
    return "monitor", "none", f"{tf} impulse valid — staged GTC monitor tier"
  if wave.get("impulse_partial"):
    return "watch", "none", f"{tf} partial impulse — staged GTC watch tier"
  return "watch", "none", f"{tf} context TF — staged GTC watch tier"


def _gtc_dca_ladder(
  direction: str,
  anchor: float,
  atr: float,
  zone_low: float,
  zone_high: float,
  fib_levels: Optional[List[float]] = None,
) -> List[dict]:
  """10/20/30/40 DCA legs — all limits, GTC."""
  legs = build_dca_ladder(direction, anchor, atr, zone_low, zone_high, fib_levels)
  for leg in legs:
    leg["order_type"] = "limit"
    leg["time_in_force"] = "GTC"
    leg["trigger"] = f"GTC limit @ {leg['price']}"
  return legs


def _tier_account_risk(base_pct: float, gtc_tier: str, honest_tier: str) -> float:
  mult = TIER_RISK_MULT.get(gtc_tier, 0.25)
  if gtc_tier == "executable" and honest_tier == "probe":
    mult *= 0.5
  return round(base_pct * mult, 3)


def build_limit_order_row(result: dict, tf: str) -> dict:
  """One GTC limit-order plan for symbol × timeframe."""
  if result.get("status") == "incomplete":
    return {
      "symbol": result.get("symbol"),
      "timeframe": tf,
      "status": "error",
      "error": result.get("error", "incomplete"),
    }

  cfg = TF_CONFIG[tf]
  style = TF_STYLE_MAP.get(tf) or f"{tf}_context"
  gtc_tier, honest_tier, tier_note = _resolve_gtc_tier(result, tf)

  ex = result.get("executive_decision") or {}
  consensus = result.get("step6_wave_consensus") or {}
  kz = result.get("step3_kill_zone") or {}
  ct = _c_targets(result)
  fib_levels = _fib_levels_from_kz(kz)
  kz_low = float(kz.get("price_low") or 0)
  kz_high = float(kz.get("price_high") or 0)
  in_zone = bool((result.get("step5_execution_validation") or {}).get("in_zone"))
  zone_low = kz_low
  zone_high = kz_high

  direction = _dir_norm(
    ex.get("direction")
    or (result.get("step8_outcomes") or {}).get("honest_summary", {}).get("primary_direction")
    or consensus.get("consensus_direction")
    or "LONG"
  )

  wave = (result.get("step2_wave_structure") or {}).get(tf) or {}
  pivots = (result.get("step2_adaptive_pivots") or {}).get(tf) or {}
  atr = float(pivots.get("atr_14") or 0)
  current = float(wave.get("current_price") or result.get("step1_htf_bias", {}).get("wave_C_current") or 0)
  if atr <= 0 and current > 0:
    atr = current * 0.01

  setups = (result.get("step8_outcomes") or {}).get("setups") or {}
  mapped_style = TF_STYLE_MAP.get(tf)
  reuse = setups.get(mapped_style) if mapped_style else None

  # Reuse honest geometry when this TF owns the style setup (gates unchanged).
  if reuse and reuse.get("timeframe") == tf and reuse.get("entry"):
    entry_anchor = float(reuse["entry"]["anchor"])
    zone = reuse["entry"].get("zone") or [kz_low, kz_high]
    zone_low, zone_high = float(zone[0]), float(zone[1])
    dca = _gtc_dca_ladder(
      direction, entry_anchor, atr, zone_low, zone_high,
      fib_levels=fib_levels,
    )
    stop = reuse.get("stop_loss") or dynamic_stop(
      direction, entry_anchor, atr, *_structure_bounds(wave, current, atr), cfg["atr_mult_sl"],
    )
    if isinstance(stop, (int, float)):
      stop = {"price": float(stop), "rule": "from setup"}
    targets = reuse.get("targets") or dynamic_targets(
      direction, entry_anchor, atr,
      harmonic_prz=_prz_tuple(_harmonic_for_tf(result, tf)),
      c_target_100=ct.get("c_target_100"),
      c_target_161=ct.get("c_target_161"),
    )
    readiness = reuse.get("readiness_score")
    indicators = "; ".join((reuse.get("indicator_signals") or [])[:3])
    honest_status = reuse.get("status")
  else:
    harm = _harmonic_for_tf(result, tf)
    if harm:
      zone_low, zone_high = float(harm["prz_low"]), float(harm["prz_high"])
      entry_anchor = (zone_low + zone_high) / 2
    elif in_zone:
      entry_anchor = current
      zone_low, zone_high = kz_low, kz_high
    else:
      entry_anchor = (kz_low + kz_high) / 2
      zone_low, zone_high = kz_low, kz_high

    s_low, s_high = _structure_bounds(wave, current, atr)
    dca = _gtc_dca_ladder(
      direction, entry_anchor, atr, zone_low, zone_high,
      fib_levels=fib_levels,
    )
    stop = dynamic_stop(direction, entry_anchor, atr, s_low, s_high, cfg["atr_mult_sl"])
    targets = dynamic_targets(
      direction, entry_anchor, atr,
      harmonic_prz=_prz_tuple(harm),
      c_target_100=ct.get("c_target_100"),
      c_target_161=ct.get("c_target_161"),
    )
    readiness = None
    indicators = wave.get("structure", "")
    honest_status = "staged"

  while len(targets) < 3:
    targets.append(targets[-1] if targets else {"price": entry_anchor, "exit_pct": 0, "rr": 0})
  rr = targets[1].get("rr", 0) if len(targets) > 1 else 0
  acct_risk = _tier_account_risk(cfg["account_risk_pct"], gtc_tier, honest_tier)
  risk = risk_package(entry_anchor, stop["price"], acct_risk)
  size_cap = TIER_SIZE_CAP[gtc_tier]
  if gtc_tier == "executable" and honest_tier == "probe":
    size_cap = min(size_cap, 50)

  return {
    "symbol": result["symbol"],
    "timeframe": tf,
    "style": style,
    "horizon": cfg["horizon"],
    "direction": direction,
    "gtc_tier": gtc_tier,
    "gtc_size_cap_pct": size_cap,
    "honest_status": honest_status if mapped_style else "n/a",
    "honest_execution_tier": honest_tier,
    "readiness_score": readiness,
    "indicator_signals": indicators,
    "consensus": consensus.get("consensus_direction"),
    "agreement_pct": consensus.get("agreement_pct"),
    "executive_verdict": ex.get("verdict"),
    "in_kill_zone": "Y" if in_zone else "N",
    "wave_structure": wave.get("structure"),
    "wave_valid": "Y" if wave.get("impulse_valid") else "N",
    "entry_anchor": entry_anchor,
    "entry_zone_low": zone_low,
    "entry_zone_high": zone_high,
    "dca_legs": dca,
    "dca_10pct_price": dca[0]["price"],
    "dca_10pct_size": dca[0]["size_pct"],
    "dca_20pct_price": dca[1]["price"],
    "dca_20pct_size": dca[1]["size_pct"],
    "dca_30pct_price": dca[2]["price"],
    "dca_30pct_size": dca[2]["size_pct"],
    "dca_40pct_price": dca[3]["price"],
    "dca_40pct_size": dca[3]["size_pct"],
    "stop_loss": stop["price"],
    "stop_rule": stop.get("rule"),
    "stop_distance_pct": stop.get("distance_pct"),
    "tp1": targets[0]["price"],
    "tp1_exit_pct": targets[0]["exit_pct"],
    "tp2": targets[1]["price"],
    "tp2_exit_pct": targets[1]["exit_pct"],
    "tp3": targets[2]["price"],
    "tp3_exit_pct": targets[2]["exit_pct"],
    "rr_tp2": rr,
    "min_rr": cfg["min_rr"],
    "account_risk_pct": acct_risk,
    "risk_sizing_rule": risk["sizing_rule"],
    "order_type": "limit",
    "time_in_force": "GTC",
    "tier_note": tier_note,
    "playbook": _playbook_line(gtc_tier, honest_tier, direction, tf, dca, stop, targets),
  }


def _prz_tuple(harm: Optional[dict]) -> Optional[Tuple[float, float]]:
  if not harm:
    return None
  return float(harm["prz_low"]), float(harm["prz_high"])


def _playbook_line(
  gtc_tier: str,
  honest_tier: str,
  direction: str,
  tf: str,
  dca: List[dict],
  stop: dict,
  targets: List[dict],
) -> str:
  legs = ", ".join(f"L{l['leg']} {l['size_pct']}%@{l['price']}" for l in dca)
  tier_lbl = gtc_tier.upper()
  if gtc_tier == "executable" and honest_tier == "probe":
    tier_lbl = "EXECUTABLE_PROBE"
  return (
    f"{tier_lbl} {direction} {tf}: GTC DCA [{legs}] · SL {stop['price']} · "
    f"TP {targets[0]['price']}/{targets[1]['price']}/{targets[2]['price']}"
  )


def build_all_limit_orders(
  results: List[dict],
  tfs: Optional[List[str]] = None,
) -> List[dict]:
  """250 rows for 50 pairs × 5 TFs (or n_pairs × len(tfs))."""
  tfs = list(tfs or ALL_TIMEFRAMES)
  rows: List[dict] = []
  for result in results:
    for tf in tfs:
      rows.append(build_limit_order_row(result, tf))
  return rows


def save_limit_orders_csv(rows: List[dict], path: str | Path) -> str:
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  if not rows:
    path.write_text("")
    return str(path)
  keys: List[str] = []
  seen = set()
  for row in rows:
    for k in row:
      if k not in seen:
        seen.add(k)
        keys.append(k)
  with path.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
  return str(path)


def export_limit_orders(
  batch_or_results: Any,
  output_dir: str | Path = "output",
  *,
  timestamp: Optional[str] = None,
  write_json: bool = False,
) -> dict:
  """Write pair×TF GTC limit order CSV + JSON summary."""
  output_dir = Path(output_dir)
  results = _normalize_results(batch_or_results)
  ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  rows = build_all_limit_orders(results)

  tier_ctr: Dict[str, int] = {}
  tf_ctr: Dict[str, int] = {}
  for r in rows:
    tier = r.get("gtc_tier", "?")
    tier_ctr[tier] = tier_ctr.get(tier, 0) + 1
    tf = r.get("timeframe", "?")
    tf_ctr[tf] = tf_ctr.get(tf, 0) + 1

  csv_path = output_dir / f"limit_orders_all_tf_{ts}.csv"
  stable_csv = output_dir / "latest_limit_orders_all_tf.csv"
  save_limit_orders_csv(rows, csv_path)
  save_limit_orders_csv(rows, stable_csv)

  meta = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "row_count": len(rows),
    "expected_rows": 50 * len(ALL_TIMEFRAMES),
    "pairs": len({r["symbol"] for r in rows if r.get("symbol")}),
    "timeframes": list(ALL_TIMEFRAMES),
    "tier_counts": tier_ctr,
    "tf_counts": tf_ctr,
    "by_gtc_tier": tier_ctr,
    "csv": str(csv_path),
    "latest_csv": str(stable_csv),
    "stable_csv": str(stable_csv),
    "dca_splits_pct": DCA_SPLITS,
  }
  meta_path = output_dir / "autodream" / "latest_limit_orders.json"
  meta_path.parent.mkdir(parents=True, exist_ok=True)
  meta_path.write_text(json.dumps(meta, indent=2))

  if write_json:
    json_path = output_dir / f"limit_orders_all_tf_{ts}.json"
    json_path.write_text(json.dumps(rows, indent=2, default=str))
    meta["json"] = str(json_path)

  return meta


def load_results_from_json(path: str | Path) -> List[dict]:
  return json.loads(Path(path).read_text())
