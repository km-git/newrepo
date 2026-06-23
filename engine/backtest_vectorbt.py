"""Optional vectorbt backtest adapter — research validation layer."""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

try:
  import vectorbt as vbt
  _HAS_VBT = True
except ImportError:
  _HAS_VBT = False


def vectorbt_available() -> bool:
  return _HAS_VBT


def backtest_setup_vectorbt(
  df: pd.DataFrame,
  setup: dict,
  lookback_bars: int = 60,
) -> dict:
  """
  Vectorized backtest using vectorbt Portfolio.from_signals.
  Returns schema compatible with native backtest_setup_on_bars.
  """
  if not _HAS_VBT:
    return {"available": False, "reason": "vectorbt not installed"}
  if df is None or len(df) < 30:
    return {"available": False, "reason": "insufficient bars"}

  direction = setup.get("direction", "LONG")
  is_long = direction in ("LONG", "BULL")
  entry_anchor = float((setup.get("entry") or {}).get("anchor") or df["Close"].iloc[-1])
  stop_price = float((setup.get("stop_loss") or {}).get("price") or entry_anchor * 0.97)
  targets = setup.get("targets") or []
  tp = float(targets[1]["price"]) if len(targets) > 1 else (
    entry_anchor * 1.02 if is_long else entry_anchor * 0.98
  )

  window = df.tail(lookback_bars).copy()
  close = window["Close"].astype(float)
  low = window["Low"].astype(float)
  high = window["High"].astype(float)

  tol = entry_anchor * 0.003
  if is_long:
    entries = (low <= entry_anchor + tol) & (close >= entry_anchor - tol)
    exits = (high >= tp) | (low <= stop_price)
  else:
    entries = (high >= entry_anchor - tol) & (close <= entry_anchor + tol)
    exits = (low <= tp) | (high >= stop_price)

  try:
    pf = vbt.Portfolio.from_signals(
      close,
      entries=entries,
      exits=exits,
      init_cash=10_000,
      fees=0.001,
      freq="1h",
    )
    trades = pf.trades
    n = int(trades.count())
    if n == 0:
      return {"available": False, "reason": "no vectorbt trades"}
    wr = float((trades.returns > 0).mean())
    return {
      "available": True,
      "engine": "vectorbt",
      "style": setup.get("style", "swing"),
      "simulated_trades": n,
      "win_rate": round(wr, 3),
      "oos_win_rate": round(wr, 3),
      "oos_trades": n,
      "avg_pnl_r": round(float(trades.returns.mean()), 3),
      "method": "vectorbt_signals",
      "validation_summary": f"vectorbt {n} trades WR {wr:.0%}",
    }
  except Exception as e:
    return {"available": False, "reason": str(e)}


def run_backtest(
  df: pd.DataFrame,
  setup: dict,
  lookback_bars: int = 60,
  full_validation: bool = True,
) -> dict:
  """Dispatch to vectorbt or native engine via BACKTEST_ENGINE env."""
  engine = os.environ.get("BACKTEST_ENGINE", "native").lower()
  if engine == "vectorbt" and _HAS_VBT:
    return backtest_setup_vectorbt(df, setup, lookback_bars)
  from engine.paper_trading import backtest_setup_on_bars
  return backtest_setup_on_bars(df, setup, lookback_bars, full_validation=full_validation)
