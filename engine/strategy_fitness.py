"""Composite strategy fitness — Swarm-style scoring from tracked outcomes."""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional, Sequence


def _env_weights() -> Dict[str, float]:
  return {
    "sharpe": float(os.environ.get("EW_FITNESS_W_SHARPE", "0.35")),
    "sortino": float(os.environ.get("EW_FITNESS_W_SORTINO", "0.25")),
    "return_pct": float(os.environ.get("EW_FITNESS_W_RETURN", "0.20")),
    "win_rate": float(os.environ.get("EW_FITNESS_W_WINRATE", "0.10")),
    "profit_factor": float(os.environ.get("EW_FITNESS_W_PF", "0.10")),
  }


def _r_returns_from_closed(closed: Sequence[dict]) -> List[float]:
  """Approximate R-multiples from tp1/sl resolution (40% off at TP1)."""
  out: List[float] = []
  for s in closed:
    st = s.get("status")
    if st not in ("tp1_hit", "sl_hit"):
      continue
    try:
      wae = float(s["wae"])
      stop = float(s["stop_loss"])
      tp1 = float(s["tp1"])
    except (KeyError, TypeError, ValueError):
      continue
    risk = abs(wae - stop)
    if risk <= 0:
      continue
    if st == "sl_hit":
      out.append(-1.0)
    else:
      reward = abs(tp1 - wae)
      partial = 0.4
      out.append((reward / risk) * partial)
  return out


def sharpe_ratio(returns: Sequence[float], annual_factor: float = 252.0) -> Optional[float]:
  if len(returns) < 2:
    return None
  mean = sum(returns) / len(returns)
  var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
  std = math.sqrt(var) if var > 0 else 0.0
  if std <= 1e-12:
    return None
  return (mean / std) * math.sqrt(annual_factor)


def sortino_ratio(returns: Sequence[float], annual_factor: float = 252.0) -> Optional[float]:
  if len(returns) < 2:
    return None
  mean = sum(returns) / len(returns)
  downs = [min(0.0, r) for r in returns]
  down_var = sum(d ** 2 for d in downs) / len(returns)
  down_std = math.sqrt(down_var) if down_var > 0 else 0.0
  if down_std <= 1e-12:
    return None
  return (mean / down_std) * math.sqrt(annual_factor)


def profit_factor(returns: Sequence[float]) -> Optional[float]:
  gains = sum(r for r in returns if r > 0)
  losses = abs(sum(r for r in returns if r < 0))
  if losses <= 1e-12:
    return None if gains <= 0 else 99.0
  return gains / losses


def normalize_component(value: Optional[float], lo: float, hi: float) -> float:
  if value is None:
    return 0.0
  if hi <= lo:
    return 0.0
  return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def composite_fitness(
  *,
  win_rate: Optional[float] = None,
  return_pct: Optional[float] = None,
  sharpe: Optional[float] = None,
  sortino: Optional[float] = None,
  profit_factor: Optional[float] = None,
  weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
  """
  Composite fitness in [0, 1] scale (Swarm Trader–style blend).
  Components normalized to comparable ranges before weighting.
  """
  w = weights or _env_weights()
  parts = {
    "sharpe": normalize_component(sharpe, -0.5, 2.0),
    "sortino": normalize_component(sortino, -0.5, 2.5),
    "return_pct": normalize_component(return_pct, -10.0, 30.0),
    "win_rate": normalize_component(win_rate, 0.35, 0.70) if win_rate is not None else 0.0,
    "profit_factor": normalize_component(profit_factor, 0.8, 2.5) if profit_factor is not None else 0.0,
  }
  score = sum(parts[k] * w.get(k, 0.0) for k in parts)
  weight_sum = sum(w.values()) or 1.0
  return {
    "fitness": round(score / weight_sum, 4),
    "components": parts,
    "weights": w,
    "raw": {
      "win_rate": win_rate,
      "return_pct": return_pct,
      "sharpe": sharpe,
      "sortino": sortino,
      "profit_factor": profit_factor,
    },
  }


def fitness_from_metrics(metrics: Optional[dict] = None) -> Dict[str, Any]:
  """Build fitness from outcome_tracker metrics + closed R-series."""
  from engine.outcome_tracker import _load_state, compute_metrics

  metrics = metrics or compute_metrics()
  overall = metrics.get("overall") or {}
  win_rate = overall.get("win_rate")

  state = _load_state()
  closed = [s for s in state.get("closed", []) if s.get("status") in ("tp1_hit", "sl_hit")]
  rets = _r_returns_from_closed(closed)
  sh = sharpe_ratio(rets)
  so = sortino_ratio(rets)
  pf = profit_factor(rets)
  cum_r = sum(rets) if rets else 0.0
  return_pct = cum_r * 100.0 / max(len(rets), 1) if rets else None

  fit = composite_fitness(
    win_rate=win_rate,
    return_pct=return_pct,
    sharpe=sh,
    sortino=so,
    profit_factor=pf,
  )
  fit["n_trades"] = len(rets)
  fit["decided"] = overall.get("decided", 0)
  return fit
