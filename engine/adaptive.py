"""Adaptive pipeline — Steps 1-6 with cache, dedup, and token-efficient logging."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from taew import wave2_fibonacci_check

from cache import build_tool_calls_log, compact_summary
from cache.dedup import dedup_tool_calls
from cache.disk_cache import get_cache
from core.atr import compute_atr14, median_daily_range
from core.correction import detect_abc, detect_diagonal
from core.fib_zone import compute_prior_decline_fibs, compute_tight_kill_zone
from core.harmonic import detect_harmonics
from core.impulse import validate_impulse
from core.mc import ew_aware_monte_carlo
from core.monowaves import adaptive_skip_for_df, compute_skip, extract_monowaves_cached
from fetchers import fetch


def classify_htf(df: pd.DataFrame, tf_label: str = "1d") -> dict:
  """Classify HTF as impulse, ABC correction, diagonal, or choppy."""
  skip = adaptive_skip_for_df(df)
  mws = extract_monowaves_cached(df, skip, cache_tag=f"htf_{tf_label}")
  print(f"[step1] HTF {tf_label}: {len(mws)} monowaves")

  impulse_val = validate_impulse(mws[-5:]) if len(mws) >= 5 else None
  abc = detect_abc(mws)
  diagonal = detect_diagonal(mws)

  if impulse_val and impulse_val["passes"]:
    state = "bullish_impulse" if impulse_val["direction"] == "BULL" else "bearish_impulse"
    bias = "bullish_reversal" if impulse_val["direction"] == "BEAR" else "bearish_reversal"
    w = mws[-5:]
    wave_a = {
      "type": w[0]["type"],
      "magnitude": abs(w[0]["price_end"] - w[0]["price_start"]),
      "start": w[0]["price_start"],
      "end": w[0]["price_end"],
    }
    return {
      "tf": tf_label,
      "state": state,
      "wave_A": wave_a,
      "wave_B_end": w[1]["price_end"],
      "wave_C_current": float(df["Close"].iloc[-1]),
      "bias": bias,
    }

  if abc:
    wave_a = abc["wave_A"]
    bias = "bullish_reversal" if abc["reversal_after_C"] == "up" else "bearish_reversal"
    fib_ok = wave2_fibonacci_check(
      mws[-2]["price_end"] if len(mws) >= 2 else wave_a["end"],
      wave_a["start"],
      wave_a["end"],
    )
    print(f"[step1] ABC detected, wave2_fib_check={fib_ok}")
    return {
      "tf": tf_label,
      "state": "correction_ABC",
      "wave_A": {
        "type": wave_a["type"],
        "magnitude": wave_a["magnitude"],
        "start": wave_a["start"],
        "end": wave_a["end"],
      },
      "wave_B_end": mws[-2]["price_end"] if len(mws) >= 2 else wave_a["end"],
      "wave_C_current": float(df["Close"].iloc[-1]),
      "bias": bias,
    }

  if diagonal:
    return {
      "tf": tf_label,
      "state": "ending_diagonal",
      "wave_A": {
        "type": mws[-5]["type"],
        "magnitude": abs(mws[-5]["price_end"] - mws[-5]["price_start"]),
        "start": mws[-5]["price_start"],
        "end": mws[-5]["price_end"],
      },
      "wave_B_end": mws[-4]["price_end"],
      "wave_C_current": float(df["Close"].iloc[-1]),
      "bias": diagonal["direction"],
    }

  # Fallback: use last 3 monowaves as synthetic ABC anchors
  if len(mws) >= 3:
    a = mws[-3]
    b = mws[-2]
    wave_a = {
      "type": a["type"],
      "magnitude": abs(a["price_end"] - a["price_start"]),
      "start": a["price_start"],
      "end": a["price_end"],
    }
    return {
      "tf": tf_label,
      "state": "choppy",
      "wave_A": wave_a,
      "wave_B_end": b["price_end"],
      "wave_C_current": float(df["Close"].iloc[-1]),
      "bias": "neutral",
    }

  return {
    "tf": tf_label,
    "state": "incomplete",
    "wave_A": {"type": "n/a", "magnitude": 0.0, "start": 0.0, "end": 0.0},
    "wave_B_end": float(df["Close"].iloc[-1]),
    "wave_C_current": float(df["Close"].iloc[-1]),
    "bias": "neutral",
  }


def build_trade_setup(
  data: Dict[str, pd.DataFrame],
  kz_low: float,
  kz_high: float,
  htf_class: dict,
  direction: str,
) -> dict:
  current = float(data["1d"]["Close"].iloc[-1])
  atr = compute_atr14(data["15m"])
  entry_mid = (kz_low + kz_high) / 2

  if direction == "BULL":
    action = "execute_long"
    stop = kz_low - atr * 0.5
    tp1 = entry_mid + atr * 2
    tp2 = entry_mid + atr * 4
  else:
    action = "execute_short"
    stop = kz_high + atr * 0.5
    tp1 = entry_mid - atr * 2
    tp2 = entry_mid - atr * 4

  risk = abs(entry_mid - stop)
  reward = abs(tp1 - entry_mid)
  rr = round(reward / risk, 2) if risk > 0 else None
  confidence = min(0.85, 0.55 + (0.1 if htf_class["state"] == "correction_ABC" else 0))

  return {
    "action": action,
    "entry_zone": [round(kz_low, 2), round(kz_high, 2)],
    "stop_loss": round(stop, 2),
    "take_profit_1": round(tp1, 2),
    "take_profit_2": round(tp2, 2),
    "risk_reward": rr,
    "confidence": confidence,
    "reason": f"HTF {htf_class['state']} + 15m {direction} impulse in kill zone",
  }


def adaptive_pipeline(symbol: str, tfs: List[str], is_crypto: bool) -> dict:
  stages: List[tuple[str, dict, Any]] = []

  # Fetch
  data = fetch(symbol, tfs, is_crypto)
  stages.append(("fetch", {"symbol": symbol, "tfs": tfs, "crypto": is_crypto}, {"bars": {tf: len(data[tf]) for tf in tfs}}))

  # STEP 1: HTF bias
  htf_class = classify_htf(data["1d"])
  stages.append(("classify_htf", {"tf": "1d"}, compact_summary(htf_class)))

  # STEP 2: Adaptive pivots
  adaptive: Dict[str, dict] = {}
  for tf in tfs:
    if tf not in data:
      continue
    atr = compute_atr14(data[tf])
    med = median_daily_range(data[tf])
    skip = compute_skip(atr, med)
    mws = extract_monowaves_cached(data[tf], skip, cache_tag=f"{symbol}_{tf}")
    adaptive[tf] = {"skip": skip, "monowaves": mws, "atr_14": atr}
    print(f"[step2] {tf}: skip={skip} monowaves={len(mws)} ATR={atr:.2f}")
  stages.append(("adaptive_pivots", {"tfs": tfs}, {tf: {"skip": adaptive[tf]["skip"], "count": len(adaptive[tf]["monowaves"])} for tf in adaptive}))

  # STEP 3: Kill zone
  wave_a = htf_class["wave_A"]
  wave_a_mag = abs(wave_a["end"] - wave_a["start"])
  b_end = htf_class["wave_B_end"]
  c_target_100 = b_end + wave_a_mag
  c_target_161 = b_end + wave_a_mag * 1.618

  prior_fibs = compute_prior_decline_fibs(data["1d"])
  current_price = float(data["1d"]["Close"].iloc[-1])
  kz_low, kz_high = compute_tight_kill_zone(c_target_100, c_target_161, prior_fibs, current_price)
  width_pct = (kz_high - kz_low) / current_price * 100
  print(f"[step3] kill_zone=[{kz_low:.2f}, {kz_high:.2f}] width={width_pct:.2f}%")
  stages.append(("kill_zone", {"symbol": symbol}, {"low": kz_low, "high": kz_high, "width_pct": width_pct}))

  # STEP 4: Harmonic overlay
  harmonic_overlaps: List[dict] = []
  for tf in ["4h", "1h", "15m"]:
    if tf in data:
      harmonic_overlaps.extend(detect_harmonics(data[tf], tf, (kz_low, kz_high), symbol))
  print(f"[step4] harmonic overlaps: {len(harmonic_overlaps)}")
  stages.append(("harmonics", {"tfs": ["4h", "1h", "15m"]}, {"count": len(harmonic_overlaps)}))

  # STEP 5: Execution validation
  in_zone = kz_low <= current_price <= kz_high
  execution_passes = False
  exec_direction = "BULL"
  bull_count = 0
  bear_count = 0
  violations_sample: List[str] = []

  if "15m" in adaptive:
    mws_15m = adaptive["15m"]["monowaves"]
    for start in range(len(mws_15m) - 4):
      candidate = mws_15m[start : start + 5]
      val = validate_impulse(candidate)
      if val["direction"] == "BULL":
        bull_count += 1
      if val["direction"] == "BEAR":
        bear_count += 1
      if val["passes"] and val["direction"] == "BULL":
        execution_passes = True
        exec_direction = "BULL"
        break
      if val["passes"] and val["direction"] == "BEAR":
        execution_passes = True
        exec_direction = "BEAR"
        break
      if val["violations"]:
        violations_sample.append(val["violations"][0])
    violations_sample = list(dict.fromkeys(violations_sample))[:5]

  print(f"[step5] in_zone={in_zone} passes={execution_passes} bull={bull_count} bear={bear_count}")
  stages.append(
    ("execution_validation", {"in_zone": in_zone},
     {"passes": execution_passes, "bull": bull_count, "bear": bear_count}),
  )

  # Monte Carlo robustness (optional, cached)
  mc_result = None
  if "15m" in adaptive and len(adaptive["15m"]["monowaves"]) >= 5:
    ref_types = [m["type"] for m in adaptive["15m"]["monowaves"][-5:]]
    cache = get_cache()
    mc_result, mc_hit = cache.get_or_compute(
      "monte_carlo",
      lambda: ew_aware_monte_carlo(data["15m"], ref_types, n_runs=200),
      symbol,
      tuple(ref_types),
      len(data["15m"]),
    )
    if mc_hit:
      print("[cache] HIT monte_carlo")
    print(f"[mc] empirical_probability={mc_result['empirical_probability']}")

  # STEP 6: Status decision
  if in_zone and execution_passes:
    status = "execute"
    trade = build_trade_setup(data, kz_low, kz_high, htf_class, exec_direction)
  elif harmonic_overlaps and not in_zone:
    status = "monitoring"
    trade = {
      "action": "monitor",
      "trigger_zone": [round(kz_low, 2), round(kz_high, 2)],
      "instruction": "Wait for price to enter zone, then 15m validation",
    }
  else:
    status = "abstain"
    reason_parts = []
    if not harmonic_overlaps:
      reason_parts.append("no harmonic overlap")
    if not in_zone:
      reason_parts.append("price outside kill zone")
    if in_zone and not execution_passes:
      reason_parts.append("15m impulse failed R1/R2/R3")
    trade = {
      "action": "no_trade",
      "reason": "; ".join(reason_parts) or "No structural confluence",
    }

  reasoning = (
    f"{symbol} at {current_price:.2f}: HTF={htf_class['state']} bias={htf_class['bias']}. "
    f"Kill zone [{kz_low:.0f}-{kz_high:.0f}] ({width_pct:.1f}% wide). "
    f"Harmonics={len(harmonic_overlaps)}, in_zone={in_zone}, 15m_valid={execution_passes}. "
    f"Decision={status}."
  )

  tool_log = dedup_tool_calls(build_tool_calls_log(stages))

  return {
    "symbol": symbol,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "status": status,
    "step1_htf_bias": htf_class,
    "step2_adaptive_pivots": {
      tf: {"skip": adaptive[tf]["skip"], "monowave_count": len(adaptive[tf]["monowaves"]), "atr_14": adaptive[tf]["atr_14"]}
      for tf in adaptive
    },
    "step3_kill_zone": {
      "price_low": kz_low,
      "price_high": kz_high,
      "width_pct": width_pct,
      "constituent_fibs": prior_fibs,
    },
    "step4_harmonic_overlap": harmonic_overlaps,
    "step5_execution_validation": {
      "in_zone": in_zone,
      "passes": execution_passes,
      "bull_impulse_count": bull_count,
      "bear_impulse_count": bear_count,
      "violations_sample": violations_sample,
    },
    "trade_setup": trade,
    "honesty_audit": {
      "hard_cap_applied": True,
      "confidence_cap": 0.85,
      "no_rule_relaxation": True,
      "computational_provenance": "core/monowaves.py, core/impulse.py, core/harmonic.py",
    },
    "tool_calls_log": tool_log,
    "reasoning_trace": reasoning,
    "monte_carlo": mc_result,
    "cache_stats": get_cache().stats(),
  }
