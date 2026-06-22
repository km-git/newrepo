"""Expert trader executive decision layer — always produces an actionable plan."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.atr import compute_atr14


def _bias_to_direction(bias: str, bull_count: int, bear_count: int) -> str:
  b = bias.lower()
  if "bullish" in b or b == "reversal_up":
    return "BULL"
  if "bearish" in b or b == "reversal_down":
    return "BEAR"
  if bull_count > bear_count:
    return "BULL"
  if bear_count > bull_count:
    return "BEAR"
  return "BULL" if bull_count >= bear_count else "BEAR"


def _nearest_fib_levels(
  current: float, fibs: Dict[str, float], direction: str
) -> Tuple[float, float, str]:
  """Pick the nearest actionable fib band below (long) or above (short) price."""
  if not fibs:
    return current * 0.99, current * 1.01, "atr_fallback"

  levels = sorted(fibs.values())
  if direction == "BULL":
    # Support cluster: levels at or below current
    supports = [lv for lv in levels if lv <= current * 1.005]
    if supports:
      anchor = supports[-1]
      band = max(current * 0.005, anchor * 0.003)
      return anchor - band, anchor + band, "nearest_support_fib"
    anchor = levels[0]
    band = max(current * 0.005, anchor * 0.003)
    return anchor - band, anchor + band, "deepest_support_fib"

  resistances = [lv for lv in levels if lv >= current * 0.995]
  if resistances:
    anchor = resistances[0]
    band = max(current * 0.005, anchor * 0.003)
    return anchor - band, anchor + band, "nearest_resistance_fib"
  anchor = levels[-1]
  band = max(current * 0.005, anchor * 0.003)
  return anchor - band, anchor + band, "highest_resistance_fib"


def _distance_pct(price: float, low: float, high: float) -> float:
  mid = (low + high) / 2
  return abs(price - mid) / price * 100


def _build_levels(
  direction: str,
  entry_low: float,
  entry_high: float,
  atr: float,
  current: float,
) -> dict:
  entry_mid = (entry_low + entry_high) / 2
  if direction == "BULL":
    stop = min(entry_low, current) - atr * 1.0
    tp1 = entry_mid + atr * 2.5
    tp2 = entry_mid + atr * 5.0
    action_base = "long"
  else:
    stop = max(entry_high, current) + atr * 1.0
    tp1 = entry_mid - atr * 2.5
    tp2 = entry_mid - atr * 5.0
    action_base = "short"

  risk = abs(entry_mid - stop)
  reward = abs(tp1 - entry_mid)
  rr = round(reward / risk, 2) if risk > 0 else 1.5

  return {
    "entry_zone": [round(entry_low, 2), round(entry_high, 2)],
    "stop_loss": round(stop, 2),
    "take_profit_1": round(tp1, 2),
    "take_profit_2": round(tp2, 2),
    "risk_reward": rr,
    "action_base": action_base,
  }


def _staged_legs(
  direction: str,
  current: float,
  kz_low: float,
  kz_high: float,
  fib_low: float,
  fib_high: float,
  atr: float,
) -> List[dict]:
  """Three-leg scale plan: probe → fib → kill zone."""
  if direction == "BULL":
    legs = [
      {"leg": 1, "label": "probe", "zone": [round(current - atr * 0.3, 2), round(current + atr * 0.1, 2)], "size_pct": 25},
      {"leg": 2, "label": "fib_support", "zone": [round(fib_low, 2), round(fib_high, 2)], "size_pct": 35},
      {"leg": 3, "label": "kill_zone", "zone": [round(kz_low, 2), round(kz_high, 2)], "size_pct": 40},
    ]
  else:
    legs = [
      {"leg": 1, "label": "probe", "zone": [round(current - atr * 0.1, 2), round(current + atr * 0.3, 2)], "size_pct": 25},
      {"leg": 2, "label": "fib_resistance", "zone": [round(fib_low, 2), round(fib_high, 2)], "size_pct": 35},
      {"leg": 3, "label": "kill_zone", "zone": [round(kz_low, 2), round(kz_high, 2)], "size_pct": 40},
    ]
  return legs


def executive_decide(
  symbol: str,
  data: Dict[str, pd.DataFrame],
  htf_class: dict,
  kz_low: float,
  kz_high: float,
  prior_fibs: Dict[str, float],
  harmonic_overlaps: List[dict],
  in_zone: bool,
  execution_passes: bool,
  exec_direction: str,
  bull_count: int,
  bear_count: int,
  violations_sample: List[str],
  mc_result: Optional[dict] = None,
) -> dict:
  """
  Expert trader decision maker. Never returns no_trade — always a playbook.
  Structural gaps are acknowledged but routed into conditional/staged plans.
  """
  current = float(data["1d"]["Close"].iloc[-1])
  atr_15m = compute_atr14(data["15m"]) if "15m" in data else compute_atr14(data["1d"])
  atr_1d = compute_atr14(data["1d"])

  direction = exec_direction if execution_passes else _bias_to_direction(
    htf_class.get("bias", "neutral"), bull_count, bear_count
  )

  fib_low, fib_high, fib_source = _nearest_fib_levels(current, prior_fibs, direction)
  zone_dist = _distance_pct(current, kz_low, kz_high)
  levels = _build_levels(direction, kz_low, kz_high, atr_15m, current)

  mc_prob = (mc_result or {}).get("empirical_probability", 0.0)
  structural_gaps: List[str] = []
  if not in_zone:
    structural_gaps.append(f"price {zone_dist:.1f}% from primary kill zone")
  if not execution_passes:
    structural_gaps.append("15m impulse pending strict validation")
  if not harmonic_overlaps:
    structural_gaps.append("no harmonic PRZ overlap yet")
  if violations_sample:
    structural_gaps.append(f"wave violations: {violations_sample[0]}")

  # --- Tier 1: Full confluence — execute now ---
  if in_zone and execution_passes:
    confidence = min(0.85, 0.70 + mc_prob * 0.15 + (0.05 if harmonic_overlaps else 0))
    action = f"execute_{levels['action_base']}"
    return {
      "status": "execute",
      "trade_setup": {
        "action": action,
        **{k: levels[k] for k in ("entry_zone", "stop_loss", "take_profit_1", "take_profit_2", "risk_reward")},
        "confidence": round(confidence, 2),
        "reason": f"Full confluence: HTF {htf_class['state']}, 15m {direction} impulse validated, in kill zone",
        "instruction": "Execute full position at market or limit inside entry zone. Trail stop after TP1.",
      },
      "executive_decision": {
        "verdict": "GO",
        "conviction": "high",
        "direction": direction,
        "position_size_pct": 100,
        "playbook": "Enter now. Manage risk with defined stop. Scale out at TP1/TP2.",
        "structural_gaps": [],
        "contingencies": [
          {"if": "15m closes below stop", "then": "exit full position, reassess HTF structure"},
          {"if": "TP1 hit", "then": "move stop to breakeven, trail remainder"},
        ],
      },
    }

  # --- Tier 2: In zone but impulse not validated — conditional execute ---
  if in_zone and not execution_passes:
    fib_levels = _build_levels(direction, fib_low, fib_high, atr_15m, current)
    confidence = min(0.72, 0.50 + mc_prob * 0.12)
    return {
      "status": "conditional_execute",
      "trade_setup": {
        "action": f"conditional_{levels['action_base']}",
        "entry_zone": levels["entry_zone"],
        "stop_loss": levels["stop_loss"],
        "take_profit_1": levels["take_profit_1"],
        "take_profit_2": levels["take_profit_2"],
        "risk_reward": levels["risk_reward"],
        "confidence": round(confidence, 2),
        "reason": f"In kill zone; awaiting 15m {direction} impulse confirmation — deploy 50% now",
        "instruction": "Place 50% size limit inside zone. Add remaining 50% on 15m impulse close confirming direction.",
        "trigger_zone": levels["entry_zone"],
      },
      "executive_decision": {
        "verdict": "CONDITIONAL_GO",
        "conviction": "medium",
        "direction": direction,
        "position_size_pct": 50,
        "playbook": "Price is at the zone. Probe with half size; add on micro-structure confirmation.",
        "structural_gaps": structural_gaps,
        "contingencies": [
          {"if": f"15m forms valid {direction} impulse", "then": "add to full size"},
          {"if": "R1/R2/R3 fails again on next sweep", "then": "hold probe only, tighten stop to 0.5 ATR"},
          {"if": "harmonic PRZ forms in zone", "then": "upgrade to full execute"},
        ],
      },
    }

  # --- Tier 3: Harmonics present, price not in zone — active monitor with entry orders ---
  if harmonic_overlaps and not in_zone:
    best = harmonic_overlaps[0]
    prz = [best["prz_low"], best["prz_high"]]
    h_levels = _build_levels(direction, prz[0], prz[1], atr_15m, current)
    confidence = min(0.68, 0.48 + len(harmonic_overlaps) * 0.05)
    return {
      "status": "active_monitor",
      "trade_setup": {
        "action": f"prepare_{levels['action_base']}",
        "entry_zone": prz,
        "stop_loss": h_levels["stop_loss"],
        "take_profit_1": h_levels["take_profit_1"],
        "take_profit_2": h_levels["take_profit_2"],
        "risk_reward": h_levels["risk_reward"],
        "confidence": round(confidence, 2),
        "reason": f"{best['pattern']} harmonic on {best['tf']} — PRZ active, price en route",
        "trigger_zone": prz,
        "instruction": f"Place GTC limit orders in PRZ [{prz[0]:.0f}-{prz[1]:.0f}]. Cancel if 1D close invalidates {htf_class['bias']} bias.",
      },
      "executive_decision": {
        "verdict": "STANDBY_ORDERS",
        "conviction": "medium",
        "direction": direction,
        "position_size_pct": 75,
        "playbook": f"Harmonic {best['pattern']} defines the entry. Set orders; let price come to you.",
        "structural_gaps": structural_gaps,
        "contingencies": [
          {"if": "price enters PRZ with 15m rejection wick", "then": "execute 75% size"},
          {"if": "price blows through PRZ without reaction", "then": "cancel limits, switch to staged fib plan"},
        ],
      },
    }

  # --- Tier 4: No ideal setup — staged entry using fib + kill zone pathway ---
  staged = _staged_legs(direction, current, kz_low, kz_high, fib_low, fib_high, atr_15m)
  primary = _build_levels(direction, fib_low, fib_high, atr_15m, current)
  confidence = min(0.62, 0.38 + mc_prob * 0.15 + (0.08 if htf_class["state"] != "choppy" else 0))

  return {
    "status": "staged_entry",
    "trade_setup": {
      "action": f"scale_{levels['action_base']}",
      "entry_zone": primary["entry_zone"],
      "stop_loss": primary["stop_loss"],
      "take_profit_1": primary["take_profit_1"],
      "take_profit_2": primary["take_profit_2"],
      "risk_reward": primary["risk_reward"],
      "confidence": round(confidence, 2),
      "reason": (
        f"HTF {htf_class['state']} → {direction} bias via {fib_source}. "
        f"Scale in across {len(staged)} levels toward kill zone [{kz_low:.0f}-{kz_high:.0f}]"
      ),
      "trigger_zone": [round(kz_low, 2), round(kz_high, 2)],
      "instruction": (
        "Deploy staged limits per scale_legs. Total risk capped at 1.5% account. "
        "Abort remaining legs if 1D close breaks stop."
      ),
    },
    "executive_decision": {
      "verdict": "STAGED_GO",
      "conviction": "moderate",
      "direction": direction,
      "position_size_pct": 100,
      "position_model": "scale_in",
      "scale_legs": staged,
      "playbook": (
        f"Expert override: no perfect confluence, but {direction} edge from HTF structure + fib pathway. "
        f"Execute systematically — probe near {current:.0f}, accumulate at fib, target kill zone."
      ),
      "structural_gaps": structural_gaps,
      "contingencies": [
        {"if": "leg 1 fills and price reverses 1 ATR against", "then": "pause legs 2-3, reassess"},
        {"if": "harmonic pattern emerges", "then": "consolidate entries into PRZ"},
        {"if": "15m impulse validates", "then": "accelerate to full size at market"},
        {"if": f"HTF bias flips from {htf_class['bias']}", "then": "flatten all legs"},
      ],
      "alternative_path": {
        "momentum_breakout": {
          "trigger": round(current + atr_1d * 0.5, 2) if direction == "BULL" else round(current - atr_1d * 0.5, 2),
          "action": f"chase_{levels['action_base']}_on_break",
          "size_pct": 30,
          "note": "If price rejects fibs and breaks 1D range, chase with reduced size",
        },
      },
    },
  }
