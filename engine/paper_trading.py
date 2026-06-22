"""Paper trading and setup-faithful historical simulation."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from engine.outcomes import STYLE_CONFIG

PAPER_LEDGER_PATH = Path("output/autodream/paper_ledger.jsonl")
PAPER_METRICS_PATH = Path("output/autodream/paper_metrics.json")
PAPER_CSV_PATH = Path("output/latest_paper_trades.csv")

STYLE_TF = {s: STYLE_CONFIG[s]["primary_tf"] for s in STYLE_CONFIG}
MAX_FORWARD_BARS = {"scalp": 48, "day_trade": 72, "swing": 30, "long_term": 12}
TIER_SIZE = {"full": 1.0, "probe": 0.35, "none": 0.0}


def _scale_geometry(
  anchor: float,
  stop: float,
  targets: List[dict],
  entry: float,
  direction: str,
) -> Tuple[float, List[dict]]:
  """Preserve stop distance and target R-multiples when entry shifts."""
  risk = abs(anchor - stop)
  if risk <= 0:
    risk = anchor * 0.01
  long = direction == "LONG"
  new_stop = entry - risk if long else entry + risk
  scaled: List[dict] = []
  for t in targets:
    reward = abs(float(t["price"]) - anchor)
    rr = float(t.get("rr", reward / risk if risk else 0))
    px = entry + reward if long else entry - reward
    scaled.append({
      "label": t.get("label", "TP"),
      "price": round(px, 6),
      "exit_pct": t.get("exit_pct", 33),
      "rr": round(rr, 2),
    })
  return new_stop, scaled


def simulate_forward(
  highs: List[float],
  lows: List[float],
  entry: float,
  stop: float,
  targets: List[dict],
  direction: str,
  max_bars: int,
) -> dict:
  """
  Walk forward bars with partial TP exits.
  Conservative: stop checked before targets each bar.
  Returns outcome, pnl_r (R-multiples), bars_held, exit_detail.
  """
  if not highs or max_bars <= 0:
    return {"outcome": "open", "pnl_r": 0.0, "bars_held": 0, "exit_detail": "no_bars"}

  risk = abs(entry - stop)
  if risk <= 0:
    return {"outcome": "open", "pnl_r": 0.0, "bars_held": 0, "exit_detail": "zero_risk"}

  remaining = 1.0
  pnl_r = 0.0
  long = direction == "LONG"
  tps = sorted(
    [(float(t["price"]), float(t.get("exit_pct", 33)) / 100.0, t.get("label", "TP")) for t in targets],
    key=lambda x: x[0],
    reverse=not long,
  )
  hit_labels: List[str] = []

  for i, (h, l) in enumerate(zip(highs[:max_bars], lows[:max_bars])):
    stopped = (l <= stop) if long else (h >= stop)
    if stopped and remaining > 0:
      pnl_r -= remaining
      return {
        "outcome": "loss",
        "pnl_r": round(pnl_r, 3),
        "bars_held": i + 1,
        "exit_detail": f"stop@{i + 1}",
        "tp_hits": hit_labels,
      }

    for tp_px, exit_frac, label in tps:
      if remaining <= 0:
        break
      hit = (h >= tp_px) if long else (l <= tp_px)
      if hit:
        frac = min(remaining, exit_frac)
        rr = abs(tp_px - entry) / risk
        pnl_r += frac * rr
        remaining -= frac
        hit_labels.append(label)

    if remaining <= 0.01:
      return {
        "outcome": "win",
        "pnl_r": round(pnl_r, 3),
        "bars_held": i + 1,
        "exit_detail": "all_tps",
        "tp_hits": hit_labels,
      }

  if remaining > 0:
    last = highs[min(len(highs), max_bars) - 1]
    unrealized = ((last - entry) / risk) if long else ((entry - last) / risk)
    pnl_r += remaining * unrealized
  return {
    "outcome": "open",
    "pnl_r": round(pnl_r, 3),
    "bars_held": min(len(highs), max_bars),
    "exit_detail": "timeout",
    "tp_hits": hit_labels,
  }


def _in_zone(bar_high: float, bar_low: float, bar_close: float, zone: List[float], near_pct: float) -> bool:
  if not zone or len(zone) < 2:
    return True
  zlo, zhi = min(zone), max(zone)
  if bar_low <= zhi and bar_high >= zlo:
    return True
  mid = (zlo + zhi) / 2
  dist = abs(bar_close - mid) / mid * 100 if mid else 99.0
  return dist <= near_pct


def backtest_setup_on_bars(
  df: pd.DataFrame,
  setup: dict,
  lookback_bars: int = 60,
) -> dict:
  """
  Setup-faithful walk-forward: enter when price touches zone,
  use scaled stop/targets from current setup geometry.
  """
  if df is None or len(df) < 25:
    return {"available": False, "reason": "insufficient bars"}

  style = setup.get("style", "swing")
  direction = setup.get("direction", "LONG")
  anchor = float(setup.get("entry", {}).get("anchor") or df["Close"].iloc[-1])
  stop = float(setup.get("stop_loss", {}).get("price") or anchor)
  targets = setup.get("targets") or []
  zone = setup.get("entry", {}).get("zone") or []
  near_pct = float(setup.get("zone_dist_pct") or 5.0) + 2.0
  max_fwd = MAX_FORWARD_BARS.get(style, 30)

  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  closes = df["Close"].values.astype(float)

  start = max(0, len(df) - lookback_bars - max_fwd - 1)
  end = len(df) - max_fwd - 1
  trades: List[dict] = []

  for i in range(start, end):
    if not _in_zone(highs[i], lows[i], closes[i], zone, near_pct):
      continue
    entry = closes[i]
    new_stop, scaled_tps = _scale_geometry(anchor, stop, targets, entry, direction)
    sub_h = highs[i + 1 : i + 1 + max_fwd].tolist()
    sub_l = lows[i + 1 : i + 1 + max_fwd].tolist()
    sim = simulate_forward(sub_h, sub_l, entry, new_stop, scaled_tps, direction, max_fwd)
    if sim["outcome"] in ("win", "loss"):
      trades.append(sim)

  wins = sum(1 for t in trades if t["outcome"] == "win")
  losses = sum(1 for t in trades if t["outcome"] == "loss")
  total = wins + losses
  win_rate = round(wins / total, 3) if total else None
  avg_pnl_r = round(sum(t["pnl_r"] for t in trades) / len(trades), 3) if trades else None

  return {
    "available": True,
    "style": style,
    "backtest_bars": lookback_bars,
    "simulated_trades": total,
    "win_rate": win_rate,
    "wins": wins,
    "losses": losses,
    "avg_pnl_r": avg_pnl_r,
    "open_skipped": len([t for t in trades if t["outcome"] == "open"]),
    "method": "setup_faithful_zone_entries",
  }


def paper_trade_setup(
  symbol: str,
  setup: dict,
  df: pd.DataFrame,
) -> dict:
  """Paper-trade the current setup from the latest bar."""
  if df is None or len(df) < 5:
    return {"symbol": symbol, "available": False, "reason": "no data"}

  direction = setup.get("direction", "LONG")
  anchor = float(setup.get("entry", {}).get("anchor") or df["Close"].iloc[-1])
  stop = float(setup.get("stop_loss", {}).get("price") or anchor)
  targets = setup.get("targets") or []
  style = setup.get("style", "swing")
  tier = setup.get("execution_tier", "none")
  size = TIER_SIZE.get(tier, 0.0)
  if setup.get("status") not in ("executable", "monitor"):
    size = 0.0

  entry = float(df["Close"].iloc[-1])
  new_stop, scaled_tps = _scale_geometry(anchor, stop, targets, entry, direction)
  max_fwd = MAX_FORWARD_BARS.get(style, 30)
  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  # Only past bars available — simulate from last bar as entry snapshot
  sim = simulate_forward(
    highs[-max_fwd:].tolist(),
    lows[-max_fwd:].tolist(),
    entry,
    new_stop,
    scaled_tps,
    direction,
    max_fwd,
  )

  return {
    "symbol": symbol,
    "style": style,
    "status": setup.get("status"),
    "execution_tier": tier,
    "direction": direction,
    "entry": round(entry, 6),
    "stop": round(new_stop, 6),
    "tp1": scaled_tps[0]["price"] if scaled_tps else None,
    "size_factor": size,
    "available": True,
    "paper_outcome": sim["outcome"],
    "paper_pnl_r": round(sim["pnl_r"] * size, 3),
    "raw_pnl_r": sim["pnl_r"],
    "bars_held": sim["bars_held"],
    "exit_detail": sim["exit_detail"],
    "tp_hits": sim.get("tp_hits", []),
    "ts": datetime.now(timezone.utc).isoformat(),
  }


def _fetch_symbol_data(symbol: str, tfs: List[str]) -> Dict[str, pd.DataFrame]:
  from fetchers import fetch

  return fetch(symbol, tfs, is_crypto=True)


def run_paper_batch(
  results: List[dict],
  fetch_missing: bool = True,
  tfs: Optional[List[str]] = None,
) -> dict:
  """Paper-trade and backtest every setup across batch results."""
  tfs = tfs or ["1w", "1d", "4h", "1h", "15m"]
  trades: List[dict] = []
  hist_by_key: Dict[str, dict] = {}
  data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}

  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    oc = r.get("step8_outcomes", {})
    setups = oc.get("setups", {})

    if fetch_missing and sym not in data_cache:
      try:
        data_cache[sym] = _fetch_symbol_data(sym, tfs)
      except Exception as e:
        data_cache[sym] = {"_error": str(e)}  # type: ignore[assignment]

    data = data_cache.get(sym, {})

    for style, setup in setups.items():
      if not setup or setup.get("status") == "not_actionable":
        continue
      setup = {**setup, "style": style}
      tf = STYLE_TF.get(style, "1d")
      df = data.get(tf) if isinstance(data, dict) else None
      if df is None or not hasattr(df, "__len__") or len(df) < 10:
        continue

      hist = backtest_setup_on_bars(df, setup)
      hist_by_key[f"{sym}:{style}"] = hist

      paper = paper_trade_setup(sym, setup, df)
      paper["hist_win_rate"] = hist.get("win_rate")
      paper["hist_trades"] = hist.get("simulated_trades")
      paper["hist_avg_pnl_r"] = hist.get("avg_pnl_r")
      paper["readiness_score"] = setup.get("readiness_score")
      paper["honest_reason"] = setup.get("honest_reason", "")[:120]
      trades.append(paper)

  closed = [t for t in trades if t.get("paper_outcome") in ("win", "loss")]
  wins = sum(1 for t in closed if t["paper_outcome"] == "win")
  total_closed = len(closed)
  report = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "pairs": len({t["symbol"] for t in trades}),
    "setups_papered": len(trades),
    "closed_trades": total_closed,
    "open_trades": len(trades) - total_closed,
    "win_rate": round(wins / total_closed, 3) if total_closed else None,
    "avg_pnl_r": round(sum(t.get("paper_pnl_r", 0) for t in trades) / len(trades), 3) if trades else None,
    "by_style": _aggregate_by(trades, "style"),
    "by_tier": _aggregate_by(trades, "execution_tier"),
    "by_status": _aggregate_by(trades, "status"),
    "trades": trades,
    "historical": hist_by_key,
  }
  return report


def _aggregate_by(trades: List[dict], key: str) -> dict:
  buckets: Dict[str, List[dict]] = {}
  for t in trades:
    buckets.setdefault(t.get(key, "?"), []).append(t)
  out = {}
  for k, items in buckets.items():
    closed = [x for x in items if x.get("paper_outcome") in ("win", "loss")]
    wins = sum(1 for x in closed if x["paper_outcome"] == "win")
    out[k] = {
      "count": len(items),
      "closed": len(closed),
      "win_rate": round(wins / len(closed), 3) if closed else None,
      "avg_pnl_r": round(sum(x.get("paper_pnl_r", 0) for x in items) / len(items), 3) if items else None,
    }
  return out


def append_paper_ledger(trades: List[dict]) -> None:
  PAPER_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
  with PAPER_LEDGER_PATH.open("a") as f:
    for t in trades:
      f.write(json.dumps(t, default=str) + "\n")


def save_paper_metrics(report: dict) -> str:
  PAPER_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
  summary = {k: v for k, v in report.items() if k != "trades"}
  PAPER_METRICS_PATH.write_text(json.dumps(summary, indent=2, default=str))
  return str(PAPER_METRICS_PATH)


def save_paper_csv(report: dict, path: str | Path = PAPER_CSV_PATH) -> str:
  trades = report.get("trades", [])
  if not trades:
    return str(path)
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  keys: List[str] = []
  seen: set[str] = set()
  for row in trades:
    for k in row:
      if k not in seen:
        seen.add(k)
        keys.append(k)
  with path.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(trades)
  return str(path)


def apply_paper_to_results(results: List[dict], report: dict) -> List[dict]:
  """Merge paper/historical metrics into step8_outcomes setups."""
  hist = report.get("historical", {})
  trade_map = {(t["symbol"], t["style"]): t for t in report.get("trades", [])}

  for r in results:
    if r.get("status") == "incomplete":
      continue
    oc = r.get("step8_outcomes", {})
    sym = r["symbol"]
    for style, setup in oc.get("setups", {}).items():
      key = f"{sym}:{style}"
      h = hist.get(key, {})
      t = trade_map.get((sym, style), {})
      if h.get("available"):
        setup["historical_edge"] = h.get("win_rate")
        setup["hist_avg_pnl_r"] = h.get("avg_pnl_r")
        setup["hist_trades"] = h.get("simulated_trades")
      if t:
        setup["paper_outcome"] = t.get("paper_outcome")
        setup["paper_pnl_r"] = t.get("paper_pnl_r")
        setup["paper_size_factor"] = t.get("size_factor")

    oc["paper_summary"] = {
      "setups_papered": sum(
        1 for s in oc.get("setups", {}).values() if s.get("paper_outcome")
      ),
      "batch_win_rate": report.get("win_rate"),
      "batch_avg_pnl_r": report.get("avg_pnl_r"),
    }
    r["step8_outcomes"] = oc

  return results


def honesty_verdict(win_rate: Optional[float], hist_trades: int, tier: str) -> str:
  if hist_trades < 3 or win_rate is None:
    return "insufficient_data"
  if win_rate >= 0.55:
    return "validated"
  if win_rate < 0.40:
    return "caution"
  if tier == "probe" and win_rate < 0.45:
    return "demote_probe"
  return "neutral"


def apply_honesty_adjustments(outcomes: dict) -> dict:
  """Honest autodream feedback on readiness and reasons."""
  for style, setup in outcomes.get("setups", {}).items():
    if not setup or setup.get("status") == "not_actionable":
      continue
    wr = setup.get("historical_edge")
    n = setup.get("hist_trades") or 0
    tier = setup.get("execution_tier", "none")
    verdict = honesty_verdict(wr, n, tier)
    setup["autodream_verdict"] = verdict

    notes: List[str] = []
    if verdict == "validated":
      boost = int((wr - 0.5) * 20) if wr else 0
      if boost > 0:
        setup["readiness_score"] = min(100, setup.get("readiness_score", 0) + boost)
        notes.append(f"hist {wr:.0%} ({n} trades) supports setup +{boost} readiness")
    elif verdict == "caution":
      notes.append(f"hist win {wr:.0%} below 40% — reduce size or wait")
      if tier == "probe":
        setup["honest_reason"] = (
          setup.get("honest_reason", "")
          + f" · autodream CAUTION: hist {wr:.0%} — probe not validated"
        )
    elif verdict == "demote_probe":
      notes.append(f"probe unvalidated: hist {wr:.0%} on {n} zone entries")
      setup["honest_reason"] = (
        setup.get("honest_reason", "")
        + f" · autodream: hist {wr:.0%} — treat probe as monitor-only"
      )
    elif verdict == "insufficient_data":
      notes.append(f"hist sample {n} trades — no autodream adjustment")

    if notes:
      setup["confidence_note"] = "; ".join(notes)

  ad = outcomes.setdefault("autodream", {})
  ad["honesty_applied"] = True
  ad["improvement_loop"] = (
    "Paper batch → setup-faithful hist backtest → honesty verdict → readiness/reason update"
  )
  return outcomes
