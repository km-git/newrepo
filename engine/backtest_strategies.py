"""Walk-forward, holdout, Monte Carlo bootstrap, and stress-test validation."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

import pandas as pd

from core.risk import MAX_STOP_PCT
from engine.trade_simulation import (
  MAX_FORWARD_BARS,
  in_zone,
  scale_geometry,
  simulate_forward,
)

# Default walk-forward folds by style (more bars on lower TFs)
DEFAULT_WF_FOLDS = {"scalp": 6, "day_trade": 5, "swing": 4, "long_term": 3, "smc": 6}
HOLDOUT_TEST_PCT = 0.30
MC_BOOTSTRAP_RUNS = 500
STRESS_STOP_WIDEN_PCT = 0.10
STRESS_SLIPPAGE_PCT = 0.05
STYLE_ATR_MULT = {"scalp": 0.8, "day_trade": 1.2, "swing": 1.8, "long_term": 2.5, "smc": 1.0}


def _honest_bar_geometry(
  df: pd.DataFrame,
  i: int,
  anchor: float,
  stop: float,
  targets: List[dict],
  direction: str,
  style: str,
) -> tuple[float, float, List[dict]]:
  """Per-bar stop/targets; ATR cap when structure-scaled stop is absurd."""
  from core.atr import compute_atr14

  entry = float(df["Close"].iloc[i])
  new_stop, scaled_tps = scale_geometry(anchor, stop, targets, entry, direction)
  max_sl = MAX_STOP_PCT.get(style, 8.0)
  stop_pct = abs(entry - new_stop) / entry * 100 if entry else 0
  if stop_pct <= max_sl * 1.2:
    return entry, new_stop, scaled_tps
  window = df.iloc[max(0, i - 30) : i + 1]
  atr = compute_atr14(window) if len(window) >= 15 else abs(entry - new_stop)
  risk = atr * STYLE_ATR_MULT.get(style, 1.2)
  new_stop = entry - risk if direction == "LONG" else entry + risk
  scaled = []
  for t in targets:
    reward = abs(float(t["price"]) - anchor)
    px = entry + reward if direction == "LONG" else entry - reward
    scaled.append({
      **t,
      "price": round(px, 6),
      "rr": round(reward / risk, 2) if risk else 0,
    })
  return entry, new_stop, scaled


def collect_zone_trades(
  df: pd.DataFrame,
  setup: dict,
  bar_start: int = 0,
  bar_end: Optional[int] = None,
  lookback_bars: Optional[int] = None,
) -> List[dict]:
  """
  Collect closed zone-entry trades on a bar index range.
  Each trade dict: outcome, pnl_r, bars_held, entry_idx.
  """
  if df is None or len(df) < 25:
    return []

  style = setup.get("style", "swing")
  direction = setup.get("direction", "LONG")
  anchor = float(setup.get("entry", {}).get("anchor") or df["Close"].iloc[-1])
  stop = float(setup.get("stop_loss", {}).get("price") or anchor)
  targets = setup.get("targets") or []
  zone = setup.get("entry", {}).get("zone") or []
  near_pct = min(float(setup.get("zone_dist_pct") or 5.0) + 2.0, MAX_STOP_PCT.get(style, 8.0))
  max_fwd = MAX_FORWARD_BARS.get(style, 30)

  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  closes = df["Close"].values.astype(float)
  n = len(df)

  if bar_end is None:
    bar_end = n - max_fwd - 1
  if lookback_bars is not None:
    bar_start = max(bar_start, bar_end - lookback_bars)

  trades: List[dict] = []
  for i in range(max(0, bar_start), min(bar_end, n - max_fwd - 1)):
    if not in_zone(highs[i], lows[i], closes[i], zone, near_pct):
      continue
    entry, new_stop, scaled_tps = _honest_bar_geometry(
      df, i, anchor, stop, targets, direction, style
    )
    sub_h = highs[i + 1 : i + 1 + max_fwd].tolist()
    sub_l = lows[i + 1 : i + 1 + max_fwd].tolist()
    sim = simulate_forward(sub_h, sub_l, entry, new_stop, scaled_tps, direction, max_fwd)
    if sim["outcome"] in ("win", "loss"):
      trades.append({**sim, "entry_idx": i, "entry": round(entry, 6)})
  return trades


def _trade_stats(trades: List[dict]) -> dict:
  closed = [t for t in trades if t.get("outcome") in ("win", "loss")]
  if not closed:
    return {
      "trades": 0,
      "wins": 0,
      "losses": 0,
      "win_rate": None,
      "avg_pnl_r": None,
      "total_pnl_r": 0.0,
    }
  wins = sum(1 for t in closed if t["outcome"] == "win")
  total = len(closed)
  pnls = [t["pnl_r"] for t in closed]
  return {
    "trades": total,
    "wins": wins,
    "losses": total - wins,
    "win_rate": round(wins / total, 3),
    "avg_pnl_r": round(sum(pnls) / total, 3),
    "total_pnl_r": round(sum(pnls), 3),
  }


def walk_forward_analysis(
  df: pd.DataFrame,
  setup: dict,
  n_folds: Optional[int] = None,
  lookback_bars: int = 120,
) -> dict:
  """
  Rolling walk-forward: each fold tests on a non-overlapping OOS window.
  Setup geometry is frozen (no re-optimization) — tests temporal robustness.
  """
  if df is None or len(df) < 40:
    return {"available": False, "reason": "insufficient bars"}

  style = setup.get("style", "swing")
  max_fwd = MAX_FORWARD_BARS.get(style, 30)
  n_folds = n_folds or DEFAULT_WF_FOLDS.get(style, 4)

  end = len(df) - max_fwd - 1
  start = max(0, end - lookback_bars)
  span = end - start
  if span < n_folds * 5:
    return {"available": False, "reason": f"need {n_folds * 5}+ bars, have {span}"}

  fold_size = span // n_folds
  folds: List[dict] = []
  oos_trades: List[dict] = []

  for f in range(n_folds):
    test_start = start + f * fold_size
    test_end = start + (f + 1) * fold_size if f < n_folds - 1 else end
    fold_trades = collect_zone_trades(df, setup, bar_start=test_start, bar_end=test_end)
    stats = _trade_stats(fold_trades)
    folds.append({
      "fold": f + 1,
      "bar_start": test_start,
      "bar_end": test_end,
      **stats,
    })
    oos_trades.extend(fold_trades)

  is_trades = collect_zone_trades(df, setup, bar_start=start, bar_end=end)
  is_stats = _trade_stats(is_trades)
  oos_stats = _trade_stats(oos_trades)

  is_wr = is_stats.get("win_rate")
  oos_wr = oos_stats.get("win_rate")
  degradation = round(is_wr - oos_wr, 3) if is_wr is not None and oos_wr is not None else None

  fold_wrs = [f["win_rate"] for f in folds if f.get("win_rate") is not None]
  consistency = round(min(fold_wrs), 3) if fold_wrs else None

  return {
    "available": True,
    "method": "walk_forward",
    "n_folds": n_folds,
    "lookback_bars": lookback_bars,
    "in_sample": is_stats,
    "out_of_sample": oos_stats,
    "degradation": degradation,
    "fold_consistency_min": consistency,
    "folds": folds,
    "oos_win_rate": oos_stats.get("win_rate"),
    "oos_trades": oos_stats.get("trades"),
    "oos_avg_pnl_r": oos_stats.get("avg_pnl_r"),
  }


def holdout_analysis(
  df: pd.DataFrame,
  setup: dict,
  test_pct: float = HOLDOUT_TEST_PCT,
  lookback_bars: int = 120,
) -> dict:
  """Temporal holdout: first (1-test_pct) in-sample, last test_pct out-of-sample."""
  if df is None or len(df) < 40:
    return {"available": False, "reason": "insufficient bars"}

  style = setup.get("style", "swing")
  max_fwd = MAX_FORWARD_BARS.get(style, 30)
  end = len(df) - max_fwd - 1
  start = max(0, end - lookback_bars)
  span = end - start
  split = start + int(span * (1 - test_pct))

  is_trades = collect_zone_trades(df, setup, bar_start=start, bar_end=split)
  oos_trades = collect_zone_trades(df, setup, bar_start=split, bar_end=end)
  is_stats = _trade_stats(is_trades)
  oos_stats = _trade_stats(oos_trades)

  is_wr = is_stats.get("win_rate")
  oos_wr = oos_stats.get("win_rate")

  return {
    "available": True,
    "method": "holdout",
    "test_pct": test_pct,
    "split_bar": split,
    "in_sample": is_stats,
    "out_of_sample": oos_stats,
    "degradation": round(is_wr - oos_wr, 3) if is_wr is not None and oos_wr is not None else None,
    "oos_win_rate": oos_stats.get("win_rate"),
    "oos_trades": oos_stats.get("trades"),
    "oos_avg_pnl_r": oos_stats.get("avg_pnl_r"),
  }


def monte_carlo_bootstrap(
  trades: List[dict],
  n_runs: int = MC_BOOTSTRAP_RUNS,
  seed: int = 42,
) -> dict:
  """Bootstrap resample trade PnLs for confidence intervals on win rate and expectancy."""
  closed = [t for t in trades if t.get("outcome") in ("win", "loss")]
  if len(closed) < 3:
    return {"available": False, "reason": f"need 3+ trades, have {len(closed)}"}

  rng = random.Random(seed)
  win_rates: List[float] = []
  avg_pnls: List[float] = []
  total_pnls: List[float] = []

  for _ in range(n_runs):
    sample = [rng.choice(closed) for _ in range(len(closed))]
    wins = sum(1 for t in sample if t["outcome"] == "win")
    pnls = [t["pnl_r"] for t in sample]
    win_rates.append(wins / len(sample))
    avg_pnls.append(sum(pnls) / len(pnls))
    total_pnls.append(sum(pnls))

  def pct(vals: List[float], p: float) -> float:
    s = sorted(vals)
    idx = int(len(s) * p)
    return round(s[min(idx, len(s) - 1)], 3)

  return {
    "available": True,
    "method": "monte_carlo_bootstrap",
    "n_runs": n_runs,
    "sample_trades": len(closed),
    "win_rate_median": pct(win_rates, 0.5),
    "win_rate_p5": pct(win_rates, 0.05),
    "win_rate_p95": pct(win_rates, 0.95),
    "avg_pnl_r_median": pct(avg_pnls, 0.5),
    "avg_pnl_r_p5": pct(avg_pnls, 0.05),
    "avg_pnl_r_p95": pct(avg_pnls, 0.95),
    "prob_positive_expectancy": round(sum(1 for x in avg_pnls if x > 0) / n_runs, 3),
  }


def perturbation_stress_test(
  df: pd.DataFrame,
  setup: dict,
  lookback_bars: int = 60,
  stop_widen_pct: float = STRESS_STOP_WIDEN_PCT,
  slippage_pct: float = STRESS_SLIPPAGE_PCT,
) -> dict:
  """
  Stress test: widen stops and apply adverse slippage on entry.
  Reports how win rate holds under worse execution assumptions.
  """
  if df is None or len(df) < 25:
    return {"available": False, "reason": "insufficient bars"}

  style = setup.get("style", "swing")
  direction = setup.get("direction", "LONG")
  anchor = float(setup.get("entry", {}).get("anchor") or df["Close"].iloc[-1])
  stop = float(setup.get("stop_loss", {}).get("price") or anchor)
  targets = setup.get("targets") or []
  zone = setup.get("entry", {}).get("zone") or []
  near_pct = min(float(setup.get("zone_dist_pct") or 5.0) + 2.0, MAX_STOP_PCT.get(style, 8.0))
  max_fwd = MAX_FORWARD_BARS.get(style, 30)
  long = direction == "LONG"

  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  closes = df["Close"].values.astype(float)
  end = len(df) - max_fwd - 1
  start = max(0, end - lookback_bars)

  base_trades: List[dict] = []
  stress_trades: List[dict] = []

  for i in range(start, end):
    if not in_zone(highs[i], lows[i], closes[i], zone, near_pct):
      continue
    entry = closes[i]
    new_stop, scaled_tps = scale_geometry(anchor, stop, targets, entry, direction)
    sub_h = highs[i + 1 : i + 1 + max_fwd].tolist()
    sub_l = lows[i + 1 : i + 1 + max_fwd].tolist()

    base = simulate_forward(sub_h, sub_l, entry, new_stop, scaled_tps, direction, max_fwd)
    if base["outcome"] not in ("win", "loss"):
      continue
    base_trades.append(base)

    # Adverse slippage on entry
    slip = entry * slippage_pct / 100
    stress_entry = entry + slip if long else entry - slip
    risk = abs(entry - new_stop)
    widen = risk * stop_widen_pct
    stress_stop = new_stop - widen if long else new_stop + widen
    _, stress_tps = scale_geometry(anchor, stop, targets, stress_entry, direction)
    stressed = simulate_forward(
      sub_h, sub_l, stress_entry, stress_stop, stress_tps, direction, max_fwd
    )
    if stressed["outcome"] in ("win", "loss"):
      stress_trades.append(stressed)

  base_stats = _trade_stats(base_trades)
  stress_stats = _trade_stats(stress_trades)
  base_wr = base_stats.get("win_rate")
  stress_wr = stress_stats.get("win_rate")

  return {
    "available": True,
    "method": "perturbation_stress",
    "stop_widen_pct": stop_widen_pct,
    "slippage_pct": slippage_pct,
    "base": base_stats,
    "stressed": stress_stats,
    "win_rate_drop": round(base_wr - stress_wr, 3) if base_wr is not None and stress_wr is not None else None,
    "stress_win_rate": stress_stats.get("win_rate"),
    "stress_avg_pnl_r": stress_stats.get("avg_pnl_r"),
  }


def anchored_walk_forward(
  df: pd.DataFrame,
  setup: dict,
  n_folds: Optional[int] = None,
  lookback_bars: int = 120,
) -> dict:
  """
  Anchored walk-forward: train window expands, test window rolls forward.
  OOS trades taken only from each fold's test segment (no overlap).
  """
  if df is None or len(df) < 40:
    return {"available": False, "reason": "insufficient bars"}

  style = setup.get("style", "swing")
  max_fwd = MAX_FORWARD_BARS.get(style, 30)
  n_folds = n_folds or DEFAULT_WF_FOLDS.get(style, 4)

  end = len(df) - max_fwd - 1
  start = max(0, end - lookback_bars)
  span = end - start
  test_size = span // (n_folds + 1)
  if test_size < 3:
    return {"available": False, "reason": "folds too small"}

  folds: List[dict] = []
  oos_trades: List[dict] = []

  for f in range(n_folds):
    train_end = start + (f + 1) * test_size
    test_start = train_end
    test_end = min(train_end + test_size, end)
    if test_end <= test_start:
      break

    train_trades = collect_zone_trades(df, setup, bar_start=start, bar_end=train_end)
    test_trades = collect_zone_trades(df, setup, bar_start=test_start, bar_end=test_end)
    folds.append({
      "fold": f + 1,
      "train_bars": train_end - start,
      "test_bars": test_end - test_start,
      "train": _trade_stats(train_trades),
      "test": _trade_stats(test_trades),
    })
    oos_trades.extend(test_trades)

  if not folds:
    return {"available": False, "reason": "no folds computed"}

  oos_stats = _trade_stats(oos_trades)
  train_all = collect_zone_trades(df, setup, bar_start=start, bar_end=start + n_folds * test_size)
  is_stats = _trade_stats(train_all)
  is_wr = is_stats.get("win_rate")
  oos_wr = oos_stats.get("win_rate")

  return {
    "available": True,
    "method": "anchored_walk_forward",
    "n_folds": len(folds),
    "in_sample": is_stats,
    "out_of_sample": oos_stats,
    "degradation": round(is_wr - oos_wr, 3) if is_wr is not None and oos_wr is not None else None,
    "folds": folds,
    "oos_win_rate": oos_stats.get("win_rate"),
    "oos_trades": oos_stats.get("trades"),
    "oos_avg_pnl_r": oos_stats.get("avg_pnl_r"),
  }


def run_all_validation(
  df: pd.DataFrame,
  setup: dict,
  lookback_bars: int = 60,
) -> dict:
  """Run full validation suite: in-sample, walk-forward, holdout, MC, stress."""
  is_trades = collect_zone_trades(df, setup, lookback_bars=lookback_bars)
  is_stats = _trade_stats(is_trades)

  wf = walk_forward_analysis(df, setup, lookback_bars=max(lookback_bars, 80))
  awf = anchored_walk_forward(df, setup, lookback_bars=max(lookback_bars, 80))
  hold = holdout_analysis(df, setup, lookback_bars=max(lookback_bars, 80))
  mc = monte_carlo_bootstrap(is_trades)
  stress = perturbation_stress_test(df, setup, lookback_bars=lookback_bars)

  # Honest composite: prefer walk-forward OOS when enough trades
  oos_wr = wf.get("oos_win_rate") if wf.get("oos_trades", 0) >= 3 else None
  if oos_wr is None and hold.get("oos_trades", 0) >= 3:
    oos_wr = hold.get("oos_win_rate")

  return {
    "available": is_stats["trades"] > 0 or wf.get("available"),
    "in_sample": {
      **is_stats,
      "method": "setup_faithful_zone_entries",
      "backtest_bars": lookback_bars,
    },
    "walk_forward": wf,
    "anchored_walk_forward": awf,
    "holdout": hold,
    "monte_carlo": mc,
    "stress": stress,
    "oos_win_rate": oos_wr,
    "oos_trades": wf.get("oos_trades") or hold.get("oos_trades"),
    "oos_avg_pnl_r": wf.get("oos_avg_pnl_r") or hold.get("oos_avg_pnl_r"),
    "wf_degradation": wf.get("degradation"),
    "stress_win_rate": stress.get("stress_win_rate"),
    "mc_win_rate_p5": mc.get("win_rate_p5") if mc.get("available") else None,
    "mc_win_rate_p95": mc.get("win_rate_p95") if mc.get("available") else None,
    "mc_prob_positive": mc.get("prob_positive_expectancy") if mc.get("available") else None,
  }


def validation_summary_line(v: dict) -> str:
  """One-line honest summary for reports."""
  if not v.get("available"):
    return v.get("reason", "validation unavailable")
  parts = []
  is_wr = (v.get("in_sample") or {}).get("win_rate")
  oos_wr = v.get("oos_win_rate")
  if is_wr is not None:
    parts.append(f"IS {is_wr:.0%}")
  if oos_wr is not None:
    parts.append(f"OOS {oos_wr:.0%}")
  deg = v.get("wf_degradation")
  if deg is not None and deg > 0.1:
    parts.append(f"degradation {deg:.0%}")
  stress_wr = v.get("stress_win_rate")
  if stress_wr is not None:
    parts.append(f"stress {stress_wr:.0%}")
  mc_p5 = v.get("mc_win_rate_p5")
  if mc_p5 is not None:
    parts.append(f"MC p5={mc_p5:.0%}")
  return " · ".join(parts) if parts else "validated"
