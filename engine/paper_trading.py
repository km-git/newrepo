"""Paper trading and setup-faithful historical simulation."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from engine.outcomes import STYLE_CONFIG
from engine.trade_simulation import (
  MAX_FORWARD_BARS,
  TIER_SIZE,
  in_zone as _in_zone,
  scale_geometry as _scale_geometry,
  simulate_forward,
)


PAPER_LEDGER_PATH = Path("output/autodream/paper_ledger.jsonl")
PAPER_METRICS_PATH = Path("output/autodream/paper_metrics.json")
PAPER_CSV_PATH = Path("output/latest_paper_trades.csv")
VALIDATION_PATH = Path("output/autodream/validation_summary.json")

STYLE_TF = {s: STYLE_CONFIG[s]["primary_tf"] for s in STYLE_CONFIG}


def backtest_setup_on_bars(
  df: pd.DataFrame,
  setup: dict,
  lookback_bars: int = 60,
  full_validation: bool = True,
) -> dict:
  """
  Setup-faithful backtest with optional walk-forward, holdout, MC, stress suite.
  """
  if df is None or len(df) < 25:
    return {"available": False, "reason": "insufficient bars"}

  if full_validation:
    from engine.backtest_strategies import run_all_validation, validation_summary_line

    v = run_all_validation(df, setup, lookback_bars=lookback_bars)
    if not v.get("available"):
      return {"available": False, "reason": v.get("reason", "no trades")}
    is_stats = v.get("in_sample") or {}
    return {
      "available": True,
      "style": setup.get("style", "swing"),
      "backtest_bars": lookback_bars,
      "simulated_trades": is_stats.get("trades", 0),
      "win_rate": is_stats.get("win_rate"),
      "wins": is_stats.get("wins", 0),
      "losses": is_stats.get("losses", 0),
      "avg_pnl_r": is_stats.get("avg_pnl_r"),
      "method": "setup_faithful_zone_entries",
      "oos_win_rate": v.get("oos_win_rate"),
      "oos_trades": v.get("oos_trades"),
      "oos_avg_pnl_r": v.get("oos_avg_pnl_r"),
      "wf_degradation": v.get("wf_degradation"),
      "stress_win_rate": v.get("stress_win_rate"),
      "mc_win_rate_p5": v.get("mc_win_rate_p5"),
      "mc_prob_positive": v.get("mc_prob_positive"),
      "validation_summary": validation_summary_line(v),
      "validation": v,
    }

  from engine.backtest_strategies import collect_zone_trades, _trade_stats

  trades = collect_zone_trades(df, setup, lookback_bars=lookback_bars)
  stats = _trade_stats(trades)
  return {
    "available": stats["trades"] > 0,
    "style": setup.get("style", "swing"),
    "backtest_bars": lookback_bars,
    "simulated_trades": stats["trades"],
    "win_rate": stats["win_rate"],
    "wins": stats["wins"],
    "losses": stats["losses"],
    "avg_pnl_r": stats["avg_pnl_r"],
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
      paper["oos_win_rate"] = hist.get("oos_win_rate")
      paper["oos_trades"] = hist.get("oos_trades")
      paper["wf_degradation"] = hist.get("wf_degradation")
      paper["stress_win_rate"] = hist.get("stress_win_rate")
      paper["mc_win_rate_p5"] = hist.get("mc_win_rate_p5")
      paper["validation_summary"] = hist.get("validation_summary")
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
    "oos_win_rate": _aggregate_oos(hist_by_key),
    "by_style": _aggregate_by(trades, "style"),
    "by_tier": _aggregate_by(trades, "execution_tier"),
    "by_status": _aggregate_by(trades, "status"),
    "trades": trades,
    "historical": hist_by_key,
  }
  _save_validation_summary(hist_by_key)
  return report


def _aggregate_oos(hist_by_key: Dict[str, dict]) -> Optional[float]:
  oos_wrs = []
  for h in hist_by_key.values():
    wr = h.get("oos_win_rate")
    if wr is not None and h.get("oos_trades", 0) >= 3:
      oos_wrs.append(wr)
  return round(sum(oos_wrs) / len(oos_wrs), 3) if oos_wrs else None


def _save_validation_summary(hist_by_key: Dict[str, dict]) -> None:
  VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
  summary = {
    k: {
      "win_rate": v.get("win_rate"),
      "oos_win_rate": v.get("oos_win_rate"),
      "oos_trades": v.get("oos_trades"),
      "wf_degradation": v.get("wf_degradation"),
      "stress_win_rate": v.get("stress_win_rate"),
      "mc_win_rate_p5": v.get("mc_win_rate_p5"),
      "validation_summary": v.get("validation_summary"),
    }
    for k, v in hist_by_key.items()
    if v.get("available")
  }
  VALIDATION_PATH.write_text(json.dumps(summary, indent=2, default=str))


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
        setup["oos_win_rate"] = h.get("oos_win_rate")
        setup["oos_trades"] = h.get("oos_trades")
        setup["wf_degradation"] = h.get("wf_degradation")
        setup["stress_win_rate"] = h.get("stress_win_rate")
        setup["mc_win_rate_p5"] = h.get("mc_win_rate_p5")
        setup["validation_summary"] = h.get("validation_summary")
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


def honesty_verdict(
  win_rate: Optional[float],
  hist_trades: int,
  tier: str,
  oos_win_rate: Optional[float] = None,
  oos_trades: int = 0,
  wf_degradation: Optional[float] = None,
  stress_win_rate: Optional[float] = None,
  mc_win_rate_p5: Optional[float] = None,
) -> str:
  """Prefer OOS walk-forward rate when available; penalize high degradation."""
  effective_wr = oos_win_rate if oos_trades >= 3 and oos_win_rate is not None else win_rate
  effective_n = oos_trades if oos_trades >= 3 else hist_trades

  if effective_n < 3 or effective_wr is None:
    return "insufficient_data"
  if wf_degradation is not None and wf_degradation > 0.20:
    return "caution"
  if stress_win_rate is not None and stress_win_rate < 0.35:
    return "caution"
  if mc_win_rate_p5 is not None and mc_win_rate_p5 < 0.30:
    return "caution"
  if effective_wr >= 0.55:
    return "validated"
  if effective_wr < 0.40:
    return "caution"
  if tier == "probe" and effective_wr < 0.45:
    return "demote_probe"
  return "neutral"


def apply_honesty_adjustments(outcomes: dict) -> dict:
  """Honest autodream feedback on readiness and reasons."""
  for style, setup in outcomes.get("setups", {}).items():
    if not setup or setup.get("status") == "not_actionable":
      continue
    wr = setup.get("oos_win_rate") if (setup.get("oos_trades") or 0) >= 3 else setup.get("historical_edge")
    n = setup.get("oos_trades") if (setup.get("oos_trades") or 0) >= 3 else (setup.get("hist_trades") or 0)
    tier = setup.get("execution_tier", "none")
    verdict = honesty_verdict(
      setup.get("historical_edge"),
      setup.get("hist_trades") or 0,
      tier,
      oos_win_rate=setup.get("oos_win_rate"),
      oos_trades=setup.get("oos_trades") or 0,
      wf_degradation=setup.get("wf_degradation"),
      stress_win_rate=setup.get("stress_win_rate"),
      mc_win_rate_p5=setup.get("mc_win_rate_p5"),
    )
    setup["autodream_verdict"] = verdict

    notes: List[str] = []
    oos_note = ""
    if (setup.get("oos_trades") or 0) >= 3 and setup.get("oos_win_rate") is not None:
      oos_note = f"OOS WF {setup['oos_win_rate']:.0%} ({setup['oos_trades']} trades)"
    if verdict == "validated":
      boost = int((wr - 0.5) * 20) if wr else 0
      if boost > 0:
        setup["readiness_score"] = min(100, setup.get("readiness_score", 0) + boost)
        notes.append(f"{'OOS' if oos_note else 'hist'} {wr:.0%} ({n} trades) supports setup +{boost} readiness")
    elif verdict == "caution":
      if setup.get("wf_degradation", 0) and setup["wf_degradation"] > 0.15:
        notes.append(f"WF degradation {setup['wf_degradation']:.0%} IS→OOS")
      if setup.get("stress_win_rate") is not None and setup["stress_win_rate"] < 0.4:
        notes.append(f"stress test {setup['stress_win_rate']:.0%} under slippage")
      notes.append(f"effective win {wr:.0%} below threshold — reduce size or wait")
      if tier == "probe":
        setup["honest_reason"] = (
          setup.get("honest_reason", "")
          + f" · autodream CAUTION: effective {wr:.0%} — probe not validated"
        )
    elif verdict == "demote_probe":
      notes.append(f"probe unvalidated: OOS/hist {wr:.0%} on {n} zone entries")
      setup["honest_reason"] = (
        setup.get("honest_reason", "")
        + f" · autodream: effective {wr:.0%} — treat probe as monitor-only"
      )
    elif verdict == "insufficient_data":
      notes.append(f"hist sample {n} trades — no autodream adjustment")

    if oos_note:
      notes.insert(0, oos_note)
    if setup.get("validation_summary") and setup["validation_summary"] not in notes:
      notes.append(setup["validation_summary"])

    if notes:
      setup["confidence_note"] = "; ".join(notes)

  ad = outcomes.setdefault("autodream", {})
  ad["honesty_applied"] = True
  ad["improvement_loop"] = (
    "Walk-forward OOS + holdout + MC bootstrap + stress → honesty verdict → monitor upgrades"
  )
  return outcomes
