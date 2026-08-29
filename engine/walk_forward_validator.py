"""Purged walk-forward validation on chronological closed setups."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from engine.effectiveness_gates import evaluate_gate, max_drawdown_pct
from engine.strategy_fitness import profit_factor, sharpe_ratio, sortino_ratio


def _parse_ts(value: str) -> float:
  if not value:
    return 0.0
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
  except (TypeError, ValueError):
    return 0.0


def _r_from_setup(setup: dict) -> Optional[float]:
  st = setup.get("status")
  if st not in ("tp1_hit", "sl_hit"):
    return None
  try:
    wae = float(setup["wae"])
    stop = float(setup["stop_loss"])
    tp1 = float(setup["tp1"])
  except (KeyError, TypeError, ValueError):
    return None
  risk = abs(wae - stop)
  if risk <= 0:
    return None
  partial = float(setup.get("tp1_exit_pct") or os.environ.get("EW_TP1_EXIT_PCT", "50")) / 100.0
  if st == "sl_hit":
    return -1.0
  reward = abs(tp1 - wae)
  return (reward / risk) * partial


def net_r_from_setup(setup: dict, *, include_fees: bool = True) -> Optional[float]:
  """Gross R from geometry resolution, minus round-trip fee drag when include_fees."""
  gross = _r_from_setup(setup)
  if gross is None or not include_fees:
    return gross
  try:
    wae = float(setup["wae"])
    stop = float(setup["stop_loss"])
  except (KeyError, TypeError, ValueError):
    return gross
  risk = abs(wae - stop)
  if risk <= 0 or wae <= 0:
    return gross
  try:
    from engine.paper_simulator import fee_rate

    fee = fee_rate()
  except Exception:
    fee = float(os.environ.get("EW_PAPER_FEE_RATE", "0.0026"))
  fee_drag_r = (2.0 * fee) / (risk / wae)
  return gross - fee_drag_r


def _metrics_from_returns(returns: Sequence[float], equity_start: float = 10000.0) -> Dict[str, Any]:
  if not returns:
    return {"n": 0}
  wins = sum(1 for r in returns if r > 0)
  losses = sum(1 for r in returns if r < 0)
  n = len(returns)
  # Fraction of equity risked per 1R — matches probe/default account_risk_pct (0.75%)
  risk_frac = float(os.environ.get("EW_WF_RISK_PCT", os.environ.get("EW_ACCOUNT_RISK_PCT", "0.75"))) / 100.0
  equity = equity_start
  curve = [equity]
  for r in returns:
    equity *= 1.0 + r * risk_frac
    curve.append(equity)
  cum_r = sum(returns)
  return {
    "n": n,
    "wins": wins,
    "losses": losses,
    "win_rate": round(wins / n, 4) if n else None,
    "return_pct": round(cum_r, 4),
    "sharpe": sharpe_ratio(returns),
    "sortino": sortino_ratio(returns),
    "profit_factor": profit_factor(returns),
    "max_drawdown_pct": max_drawdown_pct(curve),
    "returns": list(returns),
  }


def chronological_folds(
  closed: List[dict],
  n_folds: int = 5,
  purge_pct: float = 0.02,
) -> List[Tuple[List[dict], List[dict]]]:
  """
  Rolling walk-forward folds with purge gap between train and test.
  Returns list of (train_setups, test_setups) — test is always later in time.
  """
  if not closed:
    return []

  sorted_closed = sorted(
    closed,
    key=lambda s: _parse_ts(
      s.get("resolved_at") or s.get("closed_at") or s.get("recorded_at") or "",
    ),
  )
  n = len(sorted_closed)
  if n < n_folds * 4:
    split = max(1, n // n_folds)
    folds = []
    for i in range(n_folds):
      start = i * split
      end = start + split if i < n_folds - 1 else n
      test = sorted_closed[start:end]
      if test:
        purge = max(1, int(len(test) * purge_pct))
        train = sorted_closed[: max(0, start - purge)]
        folds.append((train, test))
    return folds

  fold_size = n // n_folds
  folds = []
  for i in range(n_folds):
    test_start = i * fold_size
    test_end = test_start + fold_size if i < n_folds - 1 else n
    test = sorted_closed[test_start:test_end]
    purge = max(1, int(fold_size * purge_pct))
    train_end = max(0, test_start - purge)
    train = sorted_closed[:train_end]
    if test:
      folds.append((train, test))
  return folds


def run_walk_forward_validation(
  *,
  n_folds: Optional[int] = None,
  num_trials: int = 1,
) -> Dict[str, Any]:
  """
  Walk-forward OOS validation on tracked closed setups.
  Stitches OOS returns across folds for gate evaluation.
  """
  from engine.outcome_tracker import _dedupe_closed, _load_state
  from engine.execution_gates import filter_closed_for_policy

  n_folds = n_folds or int(os.environ.get("EW_WF_FOLDS", "5"))
  state = _load_state()
  closed = _dedupe_closed([
    s for s in state.get("closed", [])
    if s.get("status") in ("tp1_hit", "sl_hit")
  ])

  closed = filter_closed_for_policy(closed)

  if len(closed) < 10:
    return {
      "ok": False,
      "reason": "insufficient_closed_setups",
      "n_closed": len(closed),
      "min_required": 10,
    }

  folds = chronological_folds(closed, n_folds=n_folds)
  fold_results: List[Dict[str, Any]] = []
  stitched_returns: List[float] = []

  for i, (_train, test) in enumerate(folds):
    rets = [r for s in test if (r := _r_from_setup(s)) is not None]
    m = _metrics_from_returns(rets)
    stitched_returns.extend(rets)
    fold_results.append({
      "fold": i + 1,
      "test_n": len(test),
      "metrics": {k: v for k, v in m.items() if k != "returns"},
    })

  stitched = _metrics_from_returns(stitched_returns)
  gate = evaluate_gate(
    n_trades=stitched.get("n", 0),
    win_rate=stitched.get("win_rate"),
    sharpe=stitched.get("sharpe"),
    profit_factor=stitched.get("profit_factor"),
    return_pct=stitched.get("return_pct"),
    max_dd_pct=stitched.get("max_drawdown_pct"),
    returns=stitched.get("returns"),
    num_trials=num_trials,
    wins=stitched.get("wins"),
  )

  # OOS efficiency: mean test Sharpe across folds
  test_sharpes = [f["metrics"].get("sharpe") for f in fold_results if f["metrics"].get("sharpe") is not None]
  mean_oos_sharpe = round(sum(test_sharpes) / len(test_sharpes), 4) if test_sharpes else None

  return {
    "ok": True,
    "n_closed": len(closed),
    "n_folds": len(folds),
    "folds": fold_results,
    "stitched_oos": {k: v for k, v in stitched.items() if k != "returns"},
    "stitched_returns_count": len(stitched_returns),
    "mean_oos_sharpe": mean_oos_sharpe,
    "deployment_gate": gate,
  }


def run_fee_walk_forward(
  *,
  timeframe: str = "1h",
  apply_policy: bool = True,
  n_folds: Optional[int] = None,
  include_fees: bool = True,
) -> Dict[str, Any]:
  """
  Purged walk-forward on policy-filtered closed setups for one timeframe.
  Uses fee-adjusted R-multiples — primary profitability proof path.
  """
  from engine.outcome_tracker import _dedupe_closed, _load_state
  from engine.execution_gates import filter_closed_for_policy

  n_folds = n_folds or int(os.environ.get("EW_WF_FOLDS", "5"))
  min_trades = int(os.environ.get("EW_WF_MIN_TRADES", "100"))
  min_expectancy_r = float(os.environ.get("EW_WF_MIN_EXPECTANCY_R", "0.0"))

  state = _load_state()
  closed = _dedupe_closed([
    s for s in state.get("closed", [])
    if s.get("status") in ("tp1_hit", "sl_hit")
    and (not timeframe or str(s.get("timeframe") or "") == timeframe)
  ])

  if apply_policy:
    closed = filter_closed_for_policy(closed)

  if len(closed) < 10:
    return {
      "ok": False,
      "reason": "insufficient_closed_setups",
      "timeframe": timeframe,
      "n_closed": len(closed),
      "apply_policy": apply_policy,
    }

  folds = chronological_folds(closed, n_folds=n_folds)
  fold_results: List[Dict[str, Any]] = []
  stitched_returns: List[float] = []

  for i, (_train, test) in enumerate(folds):
    rets = [r for s in test if (r := net_r_from_setup(s, include_fees=include_fees)) is not None]
    m = _metrics_from_returns(rets)
    exp_r = round(sum(rets) / len(rets), 4) if rets else None
    stitched_returns.extend(rets)
    fold_results.append({
      "fold": i + 1,
      "test_n": len(test),
      "expectancy_r": exp_r,
      "metrics": {k: v for k, v in m.items() if k != "returns"},
    })

  stitched = _metrics_from_returns(stitched_returns)
  expectancy_r = (
    round(sum(stitched_returns) / len(stitched_returns), 4)
    if stitched_returns else None
  )
  positive_folds = sum(1 for f in fold_results if (f.get("expectancy_r") or 0) > 0)

  passed = (
    expectancy_r is not None
    and len(stitched_returns) >= min_trades
    and expectancy_r >= min_expectancy_r
  )

  return {
    "ok": True,
    "timeframe": timeframe,
    "apply_policy": apply_policy,
    "include_fees": include_fees,
    "n_closed": len(closed),
    "n_folds": len(folds),
    "folds": fold_results,
    "stitched_oos": {k: v for k, v in stitched.items() if k != "returns"},
    "expectancy_r": expectancy_r,
    "positive_folds": positive_folds,
    "total_folds": len(fold_results),
    "gate_passed": passed,
    "thresholds": {
      "min_trades": min_trades,
      "min_expectancy_r": min_expectancy_r,
    },
  }
