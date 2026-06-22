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
from core.consensus import build_consensus
from core.cycle_confluence import build_cycle_confluence
from core.direction_resolver import resolve_expert_direction
from core.sentinel_adapter import build_sentinel_analysis
from core.correction import detect_abc, detect_diagonal
from core.fib_zone import compute_c_targets, compute_prior_decline_fibs, compute_tight_kill_zone
from core.harmonic import collect_actionable_harmonics, scan_harmonics
from core.impulse import validate_impulse
from core.mc import ew_aware_monte_carlo
from core.ew_coverage import build_adaptive_pivots
from core.market_tools import build_market_confluence
from core.monowaves import adaptive_skip_for_df, extract_monowaves_cached
from engine.autodream import enrich_outcomes_with_autodream, record_outcome
from engine.ew_matrix import DEFAULT_EW_TFS, build_ew_matrix, ew_coverage_summary
from engine.executive import executive_decide
from engine.outcomes import build_outcomes
from fetchers import fetch


def _distance_pct(price: float, low: float, high: float) -> float:
  mid = (low + high) / 2
  return abs(price - mid) / price * 100


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



def _first_usable_df(data: dict, prefer: List[str]):
  for k in prefer:
    df = data.get(k)
    if df is not None and len(df) >= 5:
      return df
  for df in data.values():
    if df is not None and len(df) >= 5:
      return df
  return None


def adaptive_pipeline(symbol: str, tfs: List[str], is_crypto: bool) -> dict:
  stages: List[tuple[str, dict, Any]] = []
  tfs = list(dict.fromkeys(tfs or DEFAULT_EW_TFS))

  # Fetch — always attempt all timeframes (partial OK)
  data = fetch(symbol, tfs, is_crypto)
  stages.append(("fetch", {"symbol": symbol, "tfs": tfs, "crypto": is_crypto},
                 {"bars": {tf: len(data[tf]) for tf in tfs if tf in data}}))

  htf_df = _first_usable_df(data, ["1d", "4h", "1h"])
  if htf_df is None or len(htf_df) < 5:
    raise ValueError(f"Insufficient OHLCV for {symbol}")

  # STEP 1: HTF bias (1d primary; 1w context when available)
  htf_class = classify_htf(htf_df, tf_label="1d" if "1d" in data else "4h")
  htf_weekly = None
  if "1w" in data and len(data["1w"]) >= 5:
    htf_weekly = classify_htf(data["1w"], tf_label="1w")
  stages.append(("classify_htf", {"tf": "1d"}, compact_summary(htf_class)))

  # STEP 2: Adaptive pivots — ALL timeframes, adaptive skip fallback
  adaptive = build_adaptive_pivots(symbol, data, tfs)
  for tf in tfs:
    ad = adaptive.get(tf, {})
    print(f"[step2] {tf}: skip={ad.get('skip', 0)} monowaves={len(ad.get('monowaves', []))} "
          f"bars={ad.get('bars', 0)} status={ad.get('status', 'n/a')}")
  stages.append(("adaptive_pivots", {"tfs": tfs},
                 {tf: {"skip": adaptive[tf]["skip"], "count": len(adaptive[tf]["monowaves"]),
                       "status": adaptive[tf].get("status")} for tf in tfs}))

  # STEP 2b: Elliott Wave matrix — guaranteed every TF
  wave_structure = build_ew_matrix(adaptive, data, tfs)
  ew_summary = ew_coverage_summary(wave_structure, tfs)
  print("[step2b] EW matrix: " + ", ".join(
    f"{tf}={wave_structure[tf].get('structure', 'n/a')}" for tf in tfs
  ))
  print(f"[step2b] EW coverage: {ew_summary['timeframes_analyzed']}/{len(tfs)} TFs "
        f"({ew_summary['coverage_pct']}%)")
  stages.append(("ew_matrix", {"symbol": symbol}, ew_summary))

  # STEP 3: Kill zone (direction-aware C targets, price-proximate cluster)
  wave_a = htf_class["wave_A"]
  b_end = htf_class["wave_B_end"]
  c_targets = compute_c_targets(wave_a, b_end, htf_class.get("bias", "neutral"), htf_class.get("state", "choppy"))
  c_target_100 = c_targets["c_target_100"]
  c_target_161 = c_targets["c_target_161"]

  prior_fibs = compute_prior_decline_fibs(htf_df)
  current_price = float(htf_df["Close"].iloc[-1])
  kz_low, kz_high, kz_meta = compute_tight_kill_zone(
    c_target_100, c_target_161, prior_fibs, current_price
  )
  width_pct = (kz_high - kz_low) / current_price * 100
  print(f"[step3] kill_zone=[{kz_low:.2f}, {kz_high:.2f}] width={width_pct:.2f}% cluster={kz_meta.get('cluster')}")
  stages.append(("kill_zone", {"symbol": symbol}, {"low": kz_low, "high": kz_high, "width_pct": width_pct, "c_targets": c_targets}))

  # STEP 4: Harmonic scan all execution TFs
  harmonic_scans: dict = {}
  for tf in ["4h", "1h", "15m"]:
    if tf in data:
      harmonic_scans[tf] = scan_harmonics(data[tf], tf, symbol, current_price, (kz_low, kz_high))
  harmonic_overlaps = collect_actionable_harmonics(list(harmonic_scans.values()))
  print(f"[step4] harmonics: {sum(s['count'] for s in harmonic_scans.values())} total, {len(harmonic_overlaps)} actionable")
  stages.append(("harmonics", {"tfs": list(harmonic_scans.keys())}, {"total": sum(s["count"] for s in harmonic_scans.values()), "actionable": len(harmonic_overlaps)}))

  # STEP 5: Execution validation
  in_zone = kz_low <= current_price <= kz_high
  execution_passes = False
  exec_direction = "BULL"
  bull_count = 0
  bear_count = 0
  violations_sample: List[str] = []

  if "15m" in adaptive and adaptive["15m"].get("monowaves"):
    mws_15m = adaptive["15m"]["monowaves"]
    best_val = None
    for start in range(len(mws_15m) - 4):
      candidate = mws_15m[start : start + 5]
      val = validate_impulse(candidate)
      if val["direction"] == "BULL":
        bull_count += 1
      if val["direction"] == "BEAR":
        bear_count += 1
      if val["passes"]:
        execution_passes = True
        exec_direction = val["direction"]
        best_val = val
        break
      if best_val is None and val["direction"] not in ("AMBIGUOUS", "n/a"):
        best_val = val
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

  # STEP 6: Multi-engine EW consensus (GitHub tools + internal)
  consensus = build_consensus(data, adaptive, symbol, timeframes=["1d", "4h", "15m"])
  stages.append(("wave_consensus", {"symbol": symbol}, compact_summary(consensus)))

  # STEP 6b: Hurst cycles + dominant-cycle phase
  cycle_confluence = build_cycle_confluence(symbol, data, tfs)
  stages.append(("cycle_confluence", {"symbol": symbol}, {
    "cycle_direction": cycle_confluence.get("cycle_direction"),
    "hurst": cycle_confluence.get("primary_hurst"),
    "phase": cycle_confluence.get("primary_phase"),
  }))

  # STEP 9 (early): Supplementary market tools for sentinel stack
  btc_1d = None
  if is_crypto and not symbol.upper().startswith("BTC"):
    try:
      btc_1d = fetch("BTC/USDT", ["1d"], True).get("1d")
    except Exception:
      pass
  market_tools = build_market_confluence(symbol, data, tfs, btc_1d=btc_1d)
  stages.append(("market_confluence", {"symbol": symbol},
                 {"boost": market_tools.get("confluence_boost"), "signals": market_tools.get("confluence_signals", [])[:3]}))

  # STEP 6d: Sentinel Trader fusion (structure + momentum + Ehlers cycle + VWAP)
  sentinel_analysis = build_sentinel_analysis(
    symbol, data, wave_structure, cycle_confluence, market_tools, consensus,
  )
  stages.append(("sentinel_analysis", {"symbol": symbol}, {
    "direction": sentinel_analysis.get("direction"),
    "confidence": sentinel_analysis.get("confidence"),
  }))

  # STEP 6c: Expert EW direction — sentinel + Hurst + EW stack (always BULL/BEAR)
  expert_direction = resolve_expert_direction(
    wave_structure=wave_structure,
    adaptive=adaptive,
    htf_class=htf_class,
    consensus=consensus,
    cycle_confluence=cycle_confluence,
    harmonic_overlaps=harmonic_overlaps,
    exec_direction=exec_direction,
    execution_passes=execution_passes,
    market_tools=market_tools,
    sentinel_analysis=sentinel_analysis,
  )
  stages.append(("expert_direction", {"symbol": symbol}, {
    "direction": expert_direction["direction"],
    "confidence": expert_direction["confidence"],
    "method": expert_direction["method"],
  }))

  # STEP 7: Executive decision — expert trader always finds a path
  decision = executive_decide(
    symbol=symbol,
    data=data,
    htf_class=htf_class,
    kz_low=kz_low,
    kz_high=kz_high,
    prior_fibs=prior_fibs,
    harmonic_overlaps=harmonic_overlaps,
    in_zone=in_zone,
    execution_passes=execution_passes,
    exec_direction=exec_direction,
    bull_count=bull_count,
    bear_count=bear_count,
    violations_sample=violations_sample,
    mc_result=mc_result,
    consensus=consensus,
    expert_direction=expert_direction,
    cycle_confluence=cycle_confluence,
  )
  status = decision["status"]
  trade = decision["trade_setup"]
  executive = decision["executive_decision"]
  print(f"[step7] executive verdict={executive['verdict']} status={status} action={trade['action']}")
  stages.append(("executive_decide", {"verdict": executive["verdict"]}, compact_summary(executive)))

  # STEP 8: Outcome-driven setups (scalp / day / swing / long-term)
  outcomes = build_outcomes(
    symbol=symbol,
    data=data,
    adaptive=adaptive,
    wave_structure=wave_structure,
    direction=executive.get("direction", exec_direction),
    kz_low=kz_low,
    kz_high=kz_high,
    harmonic_overlaps=harmonic_overlaps,
    in_zone=in_zone,
    consensus=consensus,
    c_targets=c_targets,
    executive=executive,
    market_tools=market_tools,
    expert_direction=expert_direction,
    cycle_confluence=cycle_confluence,
  )
  outcomes = enrich_outcomes_with_autodream(outcomes, symbol, data)
  record_outcome(symbol, outcomes, current_price, status)
  hs = outcomes["honest_summary"]
  print(f"[step8] outcomes: {hs['truth']}")

  reasoning = (
    f"EXECUTIVE CALL [{executive['verdict']}]: {executive['playbook']} "
    f"{symbol} @ {current_price:.2f}, {executive['direction']} bias, "
    f"conviction={executive['conviction']}, size={executive['position_size_pct']}%. "
    f"HTF={htf_class['state']}, zone_dist={_distance_pct(current_price, kz_low, kz_high):.1f}%, "
    f"harmonics={len(harmonic_overlaps)}, 15m_valid={execution_passes}. "
    f"EW consensus={consensus['consensus_direction']} ({consensus['agreement_pct']}% agree, "
    f"score={consensus['consensus_score']}). "
    f"Expert={expert_direction['direction']} ({expert_direction['confidence']:.0%}, "
    f"Hurst {cycle_confluence.get('primary_regime')}, phase {cycle_confluence.get('primary_phase')}). "
    f"Action: {trade['action']} | {trade.get('instruction', trade.get('reason', ''))} | "
    f"Outcomes: {hs['truth']}"
  )

  tool_log = dedup_tool_calls(build_tool_calls_log(stages))

  return {
    "symbol": symbol,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "status": status,
    "step1_htf_bias": htf_class,
    "step1_htf_weekly": htf_weekly,
    "step2_adaptive_pivots": {
      tf: {
        "skip": adaptive[tf]["skip"],
        "monowave_count": len(adaptive[tf]["monowaves"]),
        "atr_14": adaptive[tf].get("atr_14", 0),
        "bars": adaptive[tf].get("bars", 0),
        "status": adaptive[tf].get("status", "ok"),
      }
      for tf in tfs
    },
    "step2_wave_structure": wave_structure,
    "step2_ew_coverage": ew_summary,
    "step3_c_targets": c_targets,
    "step3_kill_zone": {
      "price_low": kz_low,
      "price_high": kz_high,
      "width_pct": width_pct,
      "constituent_fibs": prior_fibs,
      "cluster_meta": kz_meta,
      "c_target_100": c_target_100,
      "c_target_161": c_target_161,
    },
    "step4_harmonic_scan": harmonic_scans,
    "step4_harmonic_overlap": harmonic_overlaps,
    "step5_execution_validation": {
      "in_zone": in_zone,
      "passes": execution_passes,
      "exec_direction": exec_direction,
      "bull_impulse_count": bull_count,
      "bear_impulse_count": bear_count,
      "violations_sample": violations_sample,
    },
    "step6_wave_consensus": consensus,
    "step6b_cycle_confluence": cycle_confluence,
    "step6c_expert_direction": expert_direction,
    "step6d_sentinel_analysis": sentinel_analysis,
    "step9_market_confluence": market_tools,
    "step8_outcomes": outcomes,
    "trade_setup": trade,
    "executive_decision": executive,
    "honesty_audit": {
      "hard_cap_applied": True,
      "confidence_cap": 0.85,
      "no_rule_relaxation": True,
      "executive_mode": True,
      "always_actionable": True,
      "structural_gaps_disclosed": executive.get("structural_gaps", []),
      "computational_provenance": "core/consensus.py, engine/executive.py, github EW tools",
    },
    "tool_calls_log": tool_log,
    "reasoning_trace": reasoning,
    "monte_carlo": mc_result,
    "cache_stats": get_cache().stats(),
  }
