"""Recalibrate indicator weights from closed paper-ledger trades."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.indicators import collect_indicator_signals, compute_raw_indicators, zone_proximity_pct

CALIBRATION_PATH = Path("output/autodream/indicator_calibration.json")
ACCUMULATION_PATH = Path("output/autodream/calibration_accumulation.json")
PAPER_LEDGER_DEFAULT = Path("output/autodream/paper_ledger.jsonl")
LEDGER_LOOKBACK = 5000

MIN_OOS_EXECUTABLE = 0.55
MIN_OOS_EXECUTABLE_PROBE = 0.50
MIN_OOS_EXECUTABLE_FULL = 0.55
MIN_OOS_TRADES = 3
MIN_SIGNAL_SAMPLES = 15
MIN_LIFT_KEEP = 0.03
MAX_LIFT_DROP = -0.05
MIN_BOOTSTRAP_CLOSED = 30
MIN_RECALIBRATION_CLOSED = 100
SCORING_ERA_CALIBRATED = "calibrated"
SCORING_ERA_LEGACY = "legacy"

DEFAULT_STYLE_THRESHOLDS = {
  "scalp": 72,
  "day_trade": 65,
  "swing": 58,
  "long_term": 60,
}

# Regex patterns for tokens extracted from honest_reason (ledger backfill)
REASON_PATTERNS: List[Tuple[str, str]] = [
  ("in kill zone", r"in kill zone"),
  ("near zone", r"near zone"),
  ("approaching zone", r"approaching zone"),
  ("RSI bullish reset", r"RSI [\d.]+ bullish reset"),
  ("RSI momentum intact", r"RSI [\d.]+ momentum intact"),
  ("RSI oversold bounce", r"RSI [\d.]+ oversold bounce"),
  ("RSI bearish reset", r"RSI [\d.]+ bearish reset"),
  ("RSI weakness intact", r"RSI [\d.]+ weakness intact"),
  ("RSI overbought fade", r"RSI [\d.]+ overbought fade"),
  ("above EMA20/50", r"price above EMA20/50"),
  ("above EMA20", r"price above EMA20(?!\/)"),
  ("EMA20 support", r"testing EMA20 support"),
  ("below EMA20/50", r"price below EMA20/50"),
  ("below EMA20", r"price below EMA20(?!\/)"),
  ("EMA20 resistance", r"testing EMA20 resistance"),
  ("MACD rising", r"MACD histogram rising"),
  ("MACD falling", r"MACD histogram falling"),
  ("MACD positive", r"MACD positive"),
  ("MACD negative", r"MACD negative"),
  ("volume surge", r"volume surge"),
  ("volume at/above avg", r"volume at/above avg"),
  ("harmonic PRZ", r"harmonic PRZ"),
]


def _load_ledger(path: Optional[Path] = None, limit: int = LEDGER_LOOKBACK) -> List[dict]:
  path = path or PAPER_LEDGER_DEFAULT
  if not path.exists():
    return []
  rows: List[dict] = []
  with path.open() as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      try:
        rows.append(json.loads(line))
      except json.JSONDecodeError:
        continue
  return rows[-limit:]


def _tokens_from_reason(reason: str) -> set[str]:
  found: set[str] = set()
  for token, pat in REASON_PATTERNS:
    if re.search(pat, reason, re.I):
      found.add(token)
  return found


def _trade_tokens(trade: dict) -> set[str]:
  """Prefer explicit indicator_tokens logged at paper time."""
  tokens = trade.get("indicator_tokens")
  if tokens:
    return set(tokens)
  return _tokens_from_reason(str(trade.get("honest_reason", "")))


def _make_calibration_id(cal: dict) -> str:
  payload = json.dumps(
    {
      "weights": sorted((cal.get("signal_weights") or {}).items()),
      "blocked": sorted(cal.get("blocked_signals") or []),
      "thresholds": sorted((cal.get("style_thresholds") or {}).items()),
      "generation": cal.get("calibration_generation", 0),
    },
    sort_keys=True,
  )
  return hashlib.sha256(payload.encode()).hexdigest()[:12]


def filter_calibrated_ledger(ledger: Optional[List[dict]] = None) -> List[dict]:
  """Closed-trade subset scored under calibrated era (tagged at ledger append)."""
  ledger = ledger if ledger is not None else _load_ledger()
  return [t for t in ledger if t.get("scoring_era") == SCORING_ERA_CALIBRATED]


def accumulation_status(ledger: Optional[List[dict]] = None) -> dict:
  """Track progress toward clean-subset re-estimation."""
  ledger = ledger if ledger is not None else _load_ledger()
  closed = [t for t in ledger if t.get("paper_outcome") in ("win", "loss")]
  calibrated_closed = [t for t in closed if t.get("scoring_era") == SCORING_ERA_CALIBRATED]
  calibrated_wins = sum(1 for t in calibrated_closed if t["paper_outcome"] == "win")
  target = MIN_RECALIBRATION_CLOSED
  n_cal = len(calibrated_closed)
  cal = load_calibration() or {}

  return {
    "updated": datetime.now(timezone.utc).isoformat(),
    "total_closed": len(closed),
    "legacy_closed": len(closed) - n_cal,
    "calibrated_closed": n_cal,
    "calibrated_win_rate": round(calibrated_wins / n_cal, 3) if n_cal else None,
    "target_closed": target,
    "remaining_to_target": max(0, target - n_cal),
    "ready_for_clean_reestimate": n_cal >= target,
    "current_calibration_id": cal.get("calibration_id"),
    "current_generation": cal.get("calibration_generation", 0),
    "current_source": cal.get("source", "unknown"),
  }


def save_accumulation_state(status: dict, path: Optional[Path] = None) -> str:
  path = path or ACCUMULATION_PATH
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(status, indent=2, default=str))
  return str(path)


def load_accumulation_state(path: Optional[Path] = None) -> dict:
  path = path or ACCUMULATION_PATH
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return {}


def enrich_ledger_entry(
  trade: dict,
  setup: Optional[dict] = None,
  calibration: Optional[dict] = None,
) -> dict:
  """Tag ledger rows so future calibration can filter to clean calibrated-era data."""
  trade = dict(trade)
  setup = setup or {}
  cal = calibration or load_calibration()

  indicators = setup.get("indicators") or {}
  calibrated_active = bool(indicators.get("calibrated")) or bool(
    cal and cal.get("available") and cal.get("signal_weights")
  )
  trade["scoring_era"] = SCORING_ERA_CALIBRATED if calibrated_active else SCORING_ERA_LEGACY

  if cal:
    trade["calibration_id"] = cal.get("calibration_id")
    trade["calibration_generation"] = cal.get("calibration_generation", 0)
    trade["calibration_source"] = cal.get("source")

  tokens = indicators.get("active_tokens")
  if not tokens and setup.get("indicator_signals"):
    tokens = list(_tokens_from_reason(" ".join(setup.get("indicator_signals", []))))
  if tokens:
    trade["indicator_tokens"] = list(tokens)

  for key in (
    "oos_gate",
    "autodream_verdict",
    "oos_win_rate",
    "oos_trades",
    "wf_degradation",
    "validation_summary",
  ):
    if setup.get(key) is not None:
      trade[key] = setup.get(key)

  trade["ledger_schema"] = 2
  return trade


def merge_setup_metadata_into_trades(
  trades: List[dict],
  results: List[dict],
  calibration: Optional[dict] = None,
) -> List[dict]:
  """Merge post-honesty setup fields back into paper trades before ledger append."""
  cal = calibration or load_calibration()
  setup_map: Dict[tuple[str, str], dict] = {}
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r.get("symbol", "")
    for style, setup in (r.get("step8_outcomes") or {}).get("setups", {}).items():
      setup_map[(sym, style)] = setup or {}

  return [
    enrich_ledger_entry(t, setup_map.get((t.get("symbol", ""), t.get("style", ""))), cal)
    for t in trades
  ]


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
  if n <= 0:
    return 0.0
  p = wins / n
  denom = 1 + z * z / n
  centre = p + z * z / (2 * n)
  margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
  return (centre - margin) / denom


def analyze_signal_predictiveness(
  ledger: Optional[List[dict]] = None,
  min_samples: int = MIN_SIGNAL_SAMPLES,
) -> dict:
  """Score each indicator token vs closed ledger outcomes."""
  ledger = ledger if ledger is not None else _load_ledger()
  closed = [t for t in ledger if t.get("paper_outcome") in ("win", "loss")]
  if len(closed) < 30:
    return {
      "available": False,
      "reason": f"need >=30 closed trades, have {len(closed)}",
      "closed_trades": len(closed),
    }

  baseline_wins = sum(1 for t in closed if t["paper_outcome"] == "win")
  baseline_wr = baseline_wins / len(closed)

  token_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0})
  style_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0})
  readiness_buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0})

  for trade in closed:
    win = trade["paper_outcome"] == "win"
    for token in _trade_tokens(trade):
      key = "wins" if win else "losses"
      token_stats[token][key] += 1

    style = trade.get("style", "swing")
    style_stats[style]["wins" if win else "losses"] += 1

    rd = trade.get("readiness_score")
    if rd is not None:
      if rd >= 72:
        bucket = "ge72"
      elif rd >= 65:
        bucket = "65-71"
      elif rd >= 58:
        bucket = "58-64"
      else:
        bucket = "lt58"
      readiness_buckets[bucket]["wins" if win else "losses"] += 1

  kept: Dict[str, dict] = {}
  removed: Dict[str, dict] = {}
  default_weights = _default_token_weights()

  for token, stats in sorted(token_stats.items()):
    wins = stats["wins"]
    losses = stats["losses"]
    n = wins + losses
    if n < min_samples:
      continue
    wr = wins / n
    lift = wr - baseline_wr
    wilson_lb = _wilson_lower(wins, n)
    predictive = lift >= MIN_LIFT_KEEP or wilson_lb > baseline_wr
    anti = lift <= MAX_LIFT_DROP and wilson_lb < baseline_wr

    entry = {
      "win_rate": round(wr, 3),
      "lift": round(lift, 3),
      "n": n,
      "wilson_lb": round(wilson_lb, 3),
      "default_weight": default_weights.get(token, 10),
    }

    if anti:
      entry["weight"] = 0
      removed[token] = entry
    elif predictive:
      base_w = default_weights.get(token, 10)
      scale = max(0.5, min(2.0, wr / baseline_wr if baseline_wr > 0 else 1.0))
      entry["weight"] = round(base_w * scale)
      kept[token] = entry
    else:
      entry["weight"] = 0
      removed[token] = entry

  style_thresholds = dict(DEFAULT_STYLE_THRESHOLDS)
  for style, stats in style_stats.items():
    wins = stats["wins"]
    n = wins + stats["losses"]
    if n < 20:
      continue
    wr = wins / n
    if wr < baseline_wr - 0.05:
      style_thresholds[style] = max(style_thresholds.get(style, 58), 70)
    elif wr > baseline_wr + 0.08:
      style_thresholds[style] = min(style_thresholds.get(style, 58), 55)

  return {
    "available": True,
    "updated": datetime.now(timezone.utc).isoformat(),
    "closed_trades": len(closed),
    "baseline_win_rate": round(baseline_wr, 3),
    "kept_signals": kept,
    "removed_signals": removed,
    "style_thresholds": style_thresholds,
    "readiness_buckets": {
      k: {
        "win_rate": round(v["wins"] / (v["wins"] + v["losses"]), 3),
        "n": v["wins"] + v["losses"],
      }
      for k, v in readiness_buckets.items()
      if v["wins"] + v["losses"] >= 10
    },
    "min_oos_executable": MIN_OOS_EXECUTABLE,
  }


def _default_token_weights() -> Dict[str, int]:
  return {
    "in kill zone": 25,
    "near zone": 18,
    "approaching zone": 10,
    "RSI bullish reset": 20,
    "RSI momentum intact": 12,
    "RSI oversold bounce": 15,
    "RSI bearish reset": 20,
    "RSI weakness intact": 12,
    "RSI overbought fade": 15,
    "above EMA20/50": 20,
    "above EMA20": 12,
    "EMA20 support": 8,
    "below EMA20/50": 20,
    "below EMA20": 12,
    "EMA20 resistance": 8,
    "MACD rising": 20,
    "MACD falling": 20,
    "MACD positive": 10,
    "MACD negative": 10,
    "volume surge": 15,
    "volume at/above avg": 8,
    "harmonic PRZ": 0,
  }


def build_calibration(
  ledger: Optional[List[dict]] = None,
  source: str = "all_ledger",
) -> dict:
  """Full calibration document for persistence and scoring."""
  stats = analyze_signal_predictiveness(ledger)
  if not stats.get("available"):
    return stats
  stats["source"] = source
  stats["signal_weights"] = {
    k: v["weight"] for k, v in stats["kept_signals"].items() if v.get("weight", 0) > 0
  }
  stats["blocked_signals"] = list(stats["removed_signals"].keys())
  prev = load_calibration() or {}
  stats["calibration_generation"] = prev.get("calibration_generation", 0)
  if source == "calibrated_era_only":
    stats["calibration_generation"] = int(prev.get("calibration_generation", 0)) + 1
  stats["calibration_id"] = _make_calibration_id(stats)
  return stats


def save_calibration(cal: dict, path: Optional[Path] = None) -> str:
  path = path or CALIBRATION_PATH
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(cal, indent=2, default=str))
  return str(path)


def load_calibration(path: Optional[Path] = None) -> Optional[dict]:
  path = path or CALIBRATION_PATH
  if not path.exists():
    return None
  try:
    cal = json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return None
  return cal if cal.get("available") else None


def run_indicator_calibration(
  calibrated_only: bool = False,
  ledger: Optional[List[dict]] = None,
) -> dict:
  """Analyze ledger and persist calibrated weights."""
  ledger = ledger if ledger is not None else _load_ledger()
  status = accumulation_status(ledger)
  use_clean = calibrated_only or status["ready_for_clean_reestimate"]

  if use_clean:
    subset = filter_calibrated_ledger(ledger)
    source = "calibrated_era_only"
    if len([t for t in subset if t.get("paper_outcome") in ("win", "loss")]) < MIN_BOOTSTRAP_CLOSED:
      subset = ledger
      source = "all_ledger"
      use_clean = False
  else:
    subset = ledger
    source = "all_ledger"

  cal = build_calibration(subset, source=source)
  if cal.get("available"):
    save_calibration(cal)
  cal["accumulation"] = status
  cal["used_clean_subset"] = use_clean and source == "calibrated_era_only"
  return cal


def run_calibration_accumulation_cycle(
  results: Optional[List[dict]] = None,
  trades: Optional[List[dict]] = None,
  force_reestimate: bool = False,
) -> dict:
  """
  After a paper batch: update accumulation state and re-estimate from clean
  calibrated-era trades when the target is met.
  """
  ledger = _load_ledger()
  status = accumulation_status(ledger)
  status["force_reestimate"] = force_reestimate

  if trades and results:
    merged = merge_setup_metadata_into_trades(trades, results)
    status["last_batch_calibrated_appended"] = sum(
      1 for t in merged if t.get("scoring_era") == SCORING_ERA_CALIBRATED
    )

  should_reestimate = (
    force_reestimate
    or status["ready_for_clean_reestimate"]
  )
  reestimated = False
  cal_summary: dict = {}

  if should_reestimate and status["calibrated_closed"] >= MIN_BOOTSTRAP_CLOSED:
    cal = run_indicator_calibration(calibrated_only=True, ledger=ledger)
    reestimated = cal.get("used_clean_subset", False)
    cal_summary = {
      "calibration_id": cal.get("calibration_id"),
      "generation": cal.get("calibration_generation"),
      "source": cal.get("source"),
      "kept_signals": len(cal.get("kept_signals", {})),
      "removed_signals": len(cal.get("removed_signals", {})),
      "baseline_win_rate": cal.get("baseline_win_rate"),
      "closed_trades": cal.get("closed_trades"),
    }

  status["reestimated"] = reestimated
  status["calibration"] = cal_summary
  if not status["ready_for_clean_reestimate"]:
    status["next_action"] = (
      f"Run paper batches to accumulate {status['remaining_to_target']} more "
      f"calibrated-era closed trades (have {status['calibrated_closed']}/{status['target_closed']})"
    )
  elif reestimated:
    status["next_action"] = "Clean-subset calibration applied — continue accumulating for next generation"
  else:
    status["next_action"] = "Target met — re-estimation will run on next batch"

  save_accumulation_state(status)
  return status


def build_hybrid_weights(cal: Optional[dict] = None) -> Tuple[Dict[str, int], set[str], Dict[str, int]]:
  """
  Merge calibrated kept signals with reduced default weights for neutral tokens.
  Blocked anti-predictive tokens stay at zero.
  """
  cal = cal or load_calibration() or {}
  defaults = _default_token_weights()
  blocked = set(cal.get("blocked_signals") or cal.get("removed_signals", {}).keys())
  kept = cal.get("signal_weights") or {}
  hybrid: Dict[str, int] = dict(kept)
  for token, pts in defaults.items():
    if token in blocked:
      continue
    if token not in hybrid:
      hybrid[token] = max(4, pts // 2)
  thresholds = dict(DEFAULT_STYLE_THRESHOLDS)
  thresholds.update(cal.get("style_thresholds") or {})
  # Slightly lower thresholds when hybrid restores signal coverage
  for style in thresholds:
    thresholds[style] = max(52, int(thresholds[style]) - 5)
  return hybrid, blocked, thresholds


def score_indicator_confluence_calibrated(
  df: pd.DataFrame,
  direction: str,
  zone_low: float,
  zone_high: float,
  style: str,
  calibration: Optional[dict] = None,
) -> dict:
  """Score 0–100 using hybrid calibrated + default signal weights."""
  if df is None or len(df) < 20:
    return {"score": 0, "aligned": False, "signals": [], "raw": {}, "zone_dist_pct": 99.0}

  cal = calibration or load_calibration()
  raw = compute_raw_indicators(df)
  zdist = zone_proximity_pct(raw["price"], zone_low, zone_high)
  pairs = collect_indicator_signals(raw, direction, zdist)

  if not cal or not cal.get("available"):
    from core.indicators import score_indicator_confluence

    return score_indicator_confluence(df, direction, zone_low, zone_high, style)

  weights, blocked, thresholds = build_hybrid_weights(cal)
  threshold = int(thresholds.get(style, DEFAULT_STYLE_THRESHOLDS.get(style, 58)))

  score = 0
  signals: List[str] = []
  active_tokens: List[str] = []

  for token, _default_pts in pairs:
    if token in blocked:
      continue
    w = weights.get(token, 0)
    if w <= 0:
      continue
    score += w
    active_tokens.append(token)
    signals.append(_token_display(token, raw, zdist))

  score = min(score, 100)
  return {
    "score": score,
    "threshold": threshold,
    "aligned": score >= threshold,
    "signals": signals,
    "raw": raw,
    "zone_dist_pct": round(zdist, 3),
    "calibrated": True,
    "hybrid": True,
    "active_tokens": active_tokens,
    "blocked_count": sum(1 for t, _ in pairs if t in blocked),
  }


def _token_display(token: str, raw: dict, zdist: float) -> str:
  if token == "near zone":
    return f"near zone ({zdist:.1f}% away)"
  if token == "approaching zone":
    return f"approaching zone ({zdist:.1f}%)"
  if token.startswith("RSI "):
    return f"{token} (RSI {raw.get('rsi14', 0)})"
  if token == "volume surge":
    return f"volume surge {raw.get('volume_ratio', 1):.1f}x avg"
  if token == "volume at/above avg":
    return f"volume at/above avg ({raw.get('volume_ratio', 1):.1f}x)"
  return token


def apply_oos_executable_gate(setup: dict) -> dict:
  """Refuse executable label until OOS walk-forward clears tier threshold."""
  if setup.get("status") != "executable":
    return setup
  oos_n = int(setup.get("oos_trades") or 0)
  oos_wr = setup.get("oos_win_rate")
  tier = setup.get("execution_tier", "none")
  floor = MIN_OOS_EXECUTABLE_PROBE if tier == "probe" else MIN_OOS_EXECUTABLE_FULL
  if oos_n < MIN_OOS_TRADES or oos_wr is None:
    setup["status"] = "monitor"
    setup["execution_tier"] = "none"
    setup["honest_reason"] = (
      setup.get("honest_reason", "")
      + f" · OOS gate: insufficient OOS data ({oos_n} trades) — monitor until WF validates"
    )
    setup["oos_gate"] = "insufficient_oos"
    return setup
  if float(oos_wr) < floor:
    setup["status"] = "monitor"
    setup["execution_tier"] = "none"
    setup["honest_reason"] = (
      setup.get("honest_reason", "")
      + f" · OOS gate: {float(oos_wr):.0%} < {floor:.0%} ({oos_n} trades) — not executable"
    )
    setup["oos_gate"] = "below_threshold"
  else:
    setup["oos_gate"] = "passed"
  return setup


def apply_calibration_to_outcomes(outcomes: dict, calibration: Optional[dict] = None) -> dict:
  """Re-score readiness from calibrated weights (metadata only if no df)."""
  cal = calibration or load_calibration()
  if not cal or not cal.get("available"):
    return outcomes
  outcomes.setdefault("autodream", {})["indicator_calibration"] = {
    "closed_trades": cal.get("closed_trades"),
    "baseline_win_rate": cal.get("baseline_win_rate"),
    "kept_signals": len(cal.get("kept_signals", {})),
    "removed_signals": len(cal.get("removed_signals", {})),
    "min_oos_executable": cal.get("min_oos_executable"),
  }
  return outcomes
