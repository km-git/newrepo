"""Execution adapter — paper (and future live) order drain."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from engine.calibrated_execution import calibrated_size_pct
from engine.indicator_calibration import enrich_ledger_entry, load_calibration
from engine.paper_trading import append_paper_ledger, paper_trade_setup

EXEC_LOG_PATH = Path("output/autodream/execution_log.jsonl")


def _fetch_data(symbol: str, timeframe: str) -> dict:
  from fetchers import fetch

  tfs = list(dict.fromkeys(["15m", "1h", "4h", "1d", timeframe]))
  return fetch(symbol, tfs, is_crypto=True)


def _candidate_setup(candidate: dict) -> dict:
  return {
    "style": candidate.get("style", "swing"),
    "status": candidate.get("pipeline_status", "executable"),
    "execution_tier": candidate.get("execution_tier", "probe"),
    "direction": candidate.get("direction", "LONG"),
    "entry": {"anchor": candidate.get("entry")},
    "stop_loss": {"price": candidate.get("stop")},
    "targets": [{"price": candidate.get("tp1"), "rr": 2.0}] if candidate.get("tp1") else [],
    "indicator_signals": candidate.get("indicator_tokens") or [],
    "entry_signal": candidate.get("entry_signal"),
    "entry_probe": candidate.get("entry_probe"),
    "entry_grade": candidate.get("entry_grade"),
    "confluence_count": candidate.get("confluence_count"),
    "readiness_score": candidate.get("readiness_score"),
    "honest_reason": candidate.get("playbook") or candidate.get("upgrade_note"),
  }


def execute_paper(
  candidate: dict,
  data: Optional[dict] = None,
) -> dict:
  """Paper-execute one approved candidate."""
  symbol = candidate["symbol"]
  tf = candidate.get("timeframe") or "15m"
  data = data or _fetch_data(symbol, tf)
  df = data.get(tf)
  if df is None or len(df) < 5:
    return {"symbol": symbol, "available": False, "reason": f"missing {tf}"}

  setup = _candidate_setup(candidate)
  size_pct = float(candidate.get("calibrated_size_pct") or candidate.get("position_size_pct") or 50)
  size_factor = size_pct / 100
  trade = paper_trade_setup(symbol, setup, df, size_override=size_factor)
  trade["execution_source"] = candidate.get("source", "queue")
  trade["calibrated_size_pct"] = size_pct
  trade["timeframe"] = tf
  trade["entry_signal"] = candidate.get("entry_signal")
  trade["entry_probe"] = candidate.get("entry_probe")
  trade["entry_grade"] = candidate.get("entry_grade")
  trade["confluence_count"] = candidate.get("confluence_count")
  trade["executive_action"] = candidate.get("executive_action")
  trade["live_execution"] = True

  cal = load_calibration()
  trade = enrich_ledger_entry(trade, setup, cal)
  return trade


def append_execution_log(events: List[dict], path: Path = EXEC_LOG_PATH) -> None:
  if not events:
    return
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a") as f:
    for e in events:
      f.write(json.dumps(e, default=str) + "\n")


def drain_execution_queue(
  queue: dict,
  *,
  mode: str = "paper",
  max_trades: int = 5,
) -> dict:
  """Execute up to max_trades approved candidates."""
  approved = queue.get("approved", [])
  if not approved:
    return {"executed": 0, "trades": [], "skipped": 0}

  trades: List[dict] = []
  events: List[dict] = []
  data_cache: Dict[str, dict] = {}

  for cand in approved[:max_trades]:
    sym = cand["symbol"]
    if mode != "paper":
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "mode": mode,
        "status": "skipped",
        "reason": "live mode not enabled",
      })
      continue

    if sym not in data_cache:
      tf = cand.get("timeframe") or "15m"
      data_cache[sym] = _fetch_data(sym, tf)
    trade = execute_paper(cand, data_cache[sym])
    if trade.get("available"):
      trades.append(trade)
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "style": cand.get("style"),
        "mode": "paper",
        "status": "executed",
        "outcome": trade.get("paper_outcome"),
        "size_pct": trade.get("calibrated_size_pct"),
      })
    else:
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "mode": "paper",
        "status": "failed",
        "reason": trade.get("reason"),
      })

  if trades:
    append_paper_ledger(trades)
  append_execution_log(events)

  return {
    "executed": len(trades),
    "skipped": len(approved) - len(trades),
    "trades": trades,
    "events": events,
  }
