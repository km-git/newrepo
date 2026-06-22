"""Autodream: historical outcome tracking, monitoring, continuous improvement."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HISTORY_PATH = Path("output/autodream/history.jsonl")
METRICS_PATH = Path("output/autodream/metrics.json")


def _load_history(limit: int = 5000) -> List[dict]:
  if not HISTORY_PATH.exists():
    return []
  rows = []
  with HISTORY_PATH.open() as f:
    for line in f:
      line = line.strip()
      if line:
        try:
          rows.append(json.loads(line))
        except json.JSONDecodeError:
          continue
  return rows[-limit:]


def record_outcome(symbol: str, outcomes: dict, price: float, pipeline_status: str) -> None:
  """Append run to historical log for continuous learning."""
  HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
  entry = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "symbol": symbol,
    "price": price,
    "pipeline_status": pipeline_status,
    "honest_summary": outcomes.get("honest_summary", {}),
    "setups": {
      k: {
        "status": v.get("status"),
        "direction": v.get("direction"),
        "entry": v.get("entry", {}).get("anchor"),
        "stop": v.get("stop_loss", {}).get("price"),
        "tp1": (v.get("targets") or [{}])[0].get("price") if v.get("targets") else None,
        "rr": (v.get("targets") or [{}, {}])[1].get("rr") if v.get("targets") and len(v["targets"]) > 1 else None,
      }
      for k, v in outcomes.get("setups", {}).items()
    },
  }
  with HISTORY_PATH.open("a") as f:
    f.write(json.dumps(entry, default=str) + "\n")


def _simulate_leg(entry: float, stop: float, tp: float, direction: str, highs: List[float], lows: List[float]) -> str:
  """Walk forward bars: hit tp, stop, or open."""
  for h, l in zip(highs, lows):
    if direction == "LONG":
      if l <= stop:
        return "loss"
      if h >= tp:
        return "win"
    else:
      if h >= stop:
        return "loss"
      if l <= tp:
        return "win"
  return "open"


def analyze_historical(
  symbol: str,
  style: str,
  data_1d,
  lookback_bars: int = 60,
) -> dict:
  """
  Backtest similar setup geometry on recent history.
  Uses last N daily bars to estimate TP-before-SL rate for style ATR multiples.
  """
  if data_1d is None or len(data_1d) < 20:
    return {"available": False, "reason": "insufficient history"}

  from core.atr import compute_atr14

  closes = data_1d["Close"].values.astype(float)
  highs = data_1d["High"].values.astype(float)
  lows = data_1d["Low"].values.astype(float)
  atr = compute_atr14(data_1d)

  wins = losses = 0
  n = min(lookback_bars, len(closes) - 5)
  for i in range(len(closes) - n, len(closes) - 5):
    entry = closes[i]
    stop = entry - atr * 1.5
    tp = entry + atr * 3.0
    sub_h = highs[i + 1 : i + 6].tolist()
    sub_l = lows[i + 1 : i + 6].tolist()
    if not sub_h:
      continue
    r = _simulate_leg(entry, stop, tp, "LONG", sub_h, sub_l)
    if r == "win":
      wins += 1
    elif r == "loss":
      losses += 1

  total = wins + losses
  win_rate = round(wins / total, 3) if total else None

  hist = _load_history()
  sym_hist = [h for h in hist if h.get("symbol") == symbol]
  style_hist = []
  for h in sym_hist:
    s = h.get("setups", {}).get(style, {})
    if s:
      style_hist.append(s)

  return {
    "available": True,
    "style": style,
    "symbol": symbol,
    "backtest_bars": n,
    "simulated_trades": total,
    "win_rate": win_rate,
    "wins": wins,
    "losses": losses,
    "logged_setups": len(style_hist),
    "confidence_adjustment": round((win_rate - 0.5) * 0.1, 3) if win_rate is not None else 0,
    "lessons": _lessons(win_rate, style_hist, style),
    "next_review_utc": datetime.now(timezone.utc).isoformat(),
  }


def _lessons(win_rate: Optional[float], style_hist: List[dict], style: str) -> List[str]:
  lessons = []
  if win_rate is not None:
    if win_rate >= 0.55:
      lessons.append(f"{style}: historical geometry favors TP-before-SL ({win_rate:.0%})")
    elif win_rate < 0.45:
      lessons.append(f"{style}: tighten stops or wait for zone — backtest win rate {win_rate:.0%}")
  if len(style_hist) >= 3:
    dirs = [h.get("direction") for h in style_hist[-5:]]
    if dirs and len(set(dirs)) == 1:
      lessons.append(f"Consistent {dirs[0]} bias over last {len(dirs)} logged runs")
  return lessons


def _get_df(data: dict, tf: str, fallback: str = "1d"):
  """Safe DataFrame lookup — never use `or` on pandas objects."""
  df = data.get(tf)
  if df is not None and len(df) > 0:
    return df
  fb = data.get(fallback)
  return fb if fb is not None and len(fb) > 0 else None


def enrich_outcomes_with_autodream(
  outcomes: dict,
  symbol: str,
  data: dict,
) -> dict:
  """Add per-style historical analysis and global autodream block."""
  autodream_styles = {}
  for style in ("scalp", "day_trade", "swing", "long_term"):
    tf = {"scalp": "15m", "day_trade": "1h", "swing": "1d", "long_term": "1w"}.get(style, "1d")
    df = _get_df(data, tf, "1d")
    autodream_styles[style] = analyze_historical(symbol, style, df)

  # Apply confidence adjustment to executable setups
  for style, ad in autodream_styles.items():
    setup = outcomes.get("setups", {}).get(style, {})
    if not setup or setup.get("status") == "not_actionable":
      continue
    adj = ad.get("confidence_adjustment", 0) or 0
    if setup.get("risk"):
      setup["historical_edge"] = ad.get("win_rate")
      setup["confidence_note"] = f"autodream adj {adj:+.2f} from win_rate={ad.get('win_rate')}"

  outcomes["autodream"] = {
    "by_style": autodream_styles,
    "history_entries": len(_load_history()),
    "history_path": str(HISTORY_PATH),
    "improvement_loop": "Each run logs to history.jsonl; win rates adjust confidence; monitor upgrades on trigger",
  }
  return outcomes


def build_monitor_queue(results: List[dict]) -> List[dict]:
  """Active setups to watch (executable + monitor)."""
  queue = []
  for r in results:
    if r.get("status") == "incomplete":
      continue
    oc = r.get("step8_outcomes", {})
    for style, setup in oc.get("setups", {}).items():
      if setup.get("status") in ("executable", "monitor"):
        zone = setup.get("entry", {}).get("zone")
        queue.append({
          "id": f"{r['symbol']}:{style}",
          "symbol": r["symbol"],
          "style": style,
          "status": setup["status"],
          "direction": setup.get("direction"),
          "entry": setup.get("entry", {}).get("anchor"),
          "entry_zone": zone,
          "stop": setup.get("stop_loss", {}).get("price"),
          "tp1": setup["targets"][0]["price"] if setup.get("targets") else None,
          "check": setup.get("monitor", {}).get("check_interval"),
          "upgrade_if": setup.get("monitor", {}).get("upgrade_if", []),
          "invalidate_if": setup.get("monitor", {}).get("invalidate_if", []),
          "last_scan": None,
        })
  return queue


def save_monitor_queue(queue: List[dict], path: str = "output/autodream/monitor_queue.json") -> None:
  Path(path).parent.mkdir(parents=True, exist_ok=True)
  with open(path, "w") as f:
    json.dump({"updated": datetime.now(timezone.utc).isoformat(), "queue": queue}, f, indent=2)
