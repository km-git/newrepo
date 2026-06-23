"""Recalibrate indicator weights from closed paper-ledger trades."""

from __future__ import annotations

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
PAPER_LEDGER_DEFAULT = Path("output/autodream/paper_ledger.jsonl")
LEDGER_LOOKBACK = 5000

MIN_OOS_EXECUTABLE = 0.55
MIN_OOS_TRADES = 3
MIN_SIGNAL_SAMPLES = 15
MIN_LIFT_KEEP = 0.03
MAX_LIFT_DROP = -0.05

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


def _load_ledger(path: Path = PAPER_LEDGER_DEFAULT, limit: int = LEDGER_LOOKBACK) -> List[dict]:
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
    reason = str(trade.get("honest_reason", ""))
    for token in _tokens_from_reason(reason):
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


def build_calibration(ledger: Optional[List[dict]] = None) -> dict:
  """Full calibration document for persistence and scoring."""
  stats = analyze_signal_predictiveness(ledger)
  if not stats.get("available"):
    return stats
  stats["signal_weights"] = {
    k: v["weight"] for k, v in stats["kept_signals"].items() if v.get("weight", 0) > 0
  }
  stats["blocked_signals"] = list(stats["removed_signals"].keys())
  return stats


def save_calibration(cal: dict, path: Optional[Path] = None) -> str:
  path = path or CALIBRATION_PATH
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(cal, indent=2, default=str))
  return str(path)


def load_calibration(path: Path = CALIBRATION_PATH) -> Optional[dict]:
  if not path.exists():
    return None
  try:
    cal = json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return None
  return cal if cal.get("available") else None


def run_indicator_calibration() -> dict:
  """Analyze ledger and persist calibrated weights."""
  cal = build_calibration()
  if cal.get("available"):
    save_calibration(cal)
  return cal


def score_indicator_confluence_calibrated(
  df: pd.DataFrame,
  direction: str,
  zone_low: float,
  zone_high: float,
  style: str,
  calibration: Optional[dict] = None,
) -> dict:
  """Score 0–100 using ledger-validated signal weights only."""
  if df is None or len(df) < 20:
    return {"score": 0, "aligned": False, "signals": [], "raw": {}, "zone_dist_pct": 99.0}

  cal = calibration or load_calibration()
  raw = compute_raw_indicators(df)
  zdist = zone_proximity_pct(raw["price"], zone_low, zone_high)
  pairs = collect_indicator_signals(raw, direction, zdist)

  if not cal or not cal.get("signal_weights"):
    from core.indicators import score_indicator_confluence

    return score_indicator_confluence(df, direction, zone_low, zone_high, style)

  weights = cal["signal_weights"]
  blocked = set(cal.get("blocked_signals", []))
  thresholds = cal.get("style_thresholds", DEFAULT_STYLE_THRESHOLDS)
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
  """Refuse executable label until OOS walk-forward clears 55%."""
  if setup.get("status") != "executable":
    return setup
  oos_n = int(setup.get("oos_trades") or 0)
  oos_wr = setup.get("oos_win_rate")
  if oos_n < MIN_OOS_TRADES or oos_wr is None:
    setup["status"] = "monitor"
    setup["execution_tier"] = "none"
    setup["honest_reason"] = (
      setup.get("honest_reason", "")
      + f" · OOS gate: insufficient OOS data ({oos_n} trades) — monitor until WF validates"
    )
    setup["oos_gate"] = "insufficient_oos"
    return setup
  if float(oos_wr) < MIN_OOS_EXECUTABLE:
    setup["status"] = "monitor"
    setup["execution_tier"] = "none"
    setup["honest_reason"] = (
      setup.get("honest_reason", "")
      + f" · OOS gate: {float(oos_wr):.0%} < {MIN_OOS_EXECUTABLE:.0%} ({oos_n} trades) — not executable"
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
