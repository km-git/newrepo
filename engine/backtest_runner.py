"""Walk-forward backtest runner — bar-touch simulation feeding autoresearch fitness."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.strategy_fitness import composite_fitness, fitness_from_metrics


def load_limit_order_rows(path: str = "") -> List[dict]:
  p = Path(path or os.environ.get("EW_LIMIT_ORDERS_CSV", "output/latest_limit_orders_all_tf.csv"))
  if not p.exists():
    return []
  with p.open(newline="", encoding="utf-8") as f:
    return list(csv.DictReader(f))


def run_walk_forward_backtest(
  *,
  csv_path: str = "",
  equity_usd: Optional[float] = None,
  fetch_ohlc: bool = True,
  max_rows: int = 0,
) -> Dict[str, Any]:
  """
  Simulate limit-order export rows against recent OHLCV bars.
  Returns paper P&L summary + composite fitness for autoresearch.
  """
  rows = load_limit_order_rows(csv_path)
  if max_rows and len(rows) > max_rows:
    rows = rows[:max_rows]

  if not rows:
    baseline = fitness_from_metrics()
    return {
      "ok": False,
      "reason": "no_export_rows",
      "simulated": 0,
      "fitness": baseline,
    }

  from engine.paper_simulator import run_paper_simulation

  equity = equity_usd
  if equity is None and os.environ.get("ACCOUNT_EQUITY"):
    equity = float(os.environ["ACCOUNT_EQUITY"])

  paper = run_paper_simulation(
    rows=rows,
    equity_usd=equity,
    fetch_ohlc=fetch_ohlc,
  )

  wins = int(paper.get("wins") or 0)
  losses = int(paper.get("losses") or 0)
  total = wins + losses
  win_rate = round(wins / total, 4) if total else None

  fitness = composite_fitness(
    win_rate=win_rate,
    return_pct=paper.get("return_pct"),
    profit_factor=paper.get("profit_factor"),
    sharpe=paper.get("sharpe"),
    sortino=paper.get("sortino"),
  )

  return {
    "ok": True,
    "simulated": paper.get("simulated", 0),
    "wins": wins,
    "losses": losses,
    "win_rate": win_rate,
    "realized_pnl_usd": paper.get("realized_pnl_usd"),
    "return_pct": paper.get("return_pct"),
    "paper": paper,
    "fitness": fitness,
    "rows_tested": len(rows),
  }


def backtest_for_autoresearch(note: str = "walk_forward") -> Dict[str, Any]:
  """Convenience hook: run backtest and return fitness dict for experiment logging."""
  result = run_walk_forward_backtest(fetch_ohlc=os.environ.get("EW_BACKTEST_FETCH_OHLC", "1") == "1")
  result["experiment_note"] = note
  return result
