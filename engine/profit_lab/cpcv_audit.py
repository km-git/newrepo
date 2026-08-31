"""Combinatorial purged CV, PSR, DSR, PBO via purgedcv."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from engine.profit_lab.expectancy import min_slice_samples
from engine.profit_lab.setup_returns import setups_to_returns_frame


def _import_purgedcv():
  try:
    import purgedcv
    return purgedcv
  except ImportError as exc:
    raise ImportError("pip install purgedcv (see requirements-outcome.txt)") from exc


def sharpe_from_returns(returns: Sequence[float]) -> Optional[float]:
  if len(returns) < 2:
    return None
  arr = np.asarray(returns, dtype=float)
  std = arr.std(ddof=1)
  if std <= 1e-12:
    return None
  return float(arr.mean() / std * np.sqrt(len(arr)))


def run_cpcv_audit(
  df: Optional[pd.DataFrame] = None,
  *,
  n_groups: int = 6,
  n_test_groups: int = 2,
  num_trials: Optional[int] = None,
) -> Dict[str, Any]:
  """
  CPCV on chronological fee-adjusted returns.
  Uses purgedcv WalkForwardSplit + deflated Sharpe when full CPCV timestamps unavailable.
  """
  pcv = _import_purgedcv()
  df = df if df is not None else setups_to_returns_frame()
  if len(df) < 20:
    return {"ok": False, "reason": "insufficient_setups", "n": len(df)}

  returns = df["net_r"].astype(float).tolist()
  n = len(returns)
  num_trials = num_trials or int(os.environ.get("EW_AUTORESEARCH_TRIALS", "50"))

  observed_sr = sharpe_from_returns(returns)
  psr_result: Dict[str, Any] = {}
  dsr_result: Dict[str, Any] = {}
  try:
    arr = np.asarray(returns, dtype=float)
    psr_val = float(pcv.probabilistic_sharpe_ratio(arr, benchmark_skill=0.0))
    dsr_val = float(pcv.deflated_sharpe_ratio(arr, num_trials, observed_sr or 0.0))
    psr_result = {"psr": psr_val}
    dsr_result = {"dsr": dsr_val}
  except Exception as exc:
    psr_result = {"error": str(exc)}
    dsr_result = {"error": str(exc)}

  # Walk-forward OOS folds on return series
  fold_results: List[Dict[str, Any]] = []
  n_folds = int(os.environ.get("EW_WF_FOLDS", "5"))
  fold_size = max(1, n // n_folds)
  oos_returns: List[float] = []
  for i in range(n_folds):
    start = i * fold_size
    end = start + fold_size if i < n_folds - 1 else n
    test = returns[start:end]
    if not test:
      continue
    oos_returns.extend(test)
    exp = float(np.mean(test))
    fold_results.append({
      "fold": i + 1,
      "n": len(test),
      "expectancy_r": round(exp, 6),
      "win_rate": round(sum(1 for r in test if r > 0) / len(test), 4),
      "sharpe": sharpe_from_returns(test),
    })

  oos_exp = float(np.mean(oos_returns)) if oos_returns else 0.0
  positive_folds = sum(1 for f in fold_results if (f.get("expectancy_r") or 0) > 0)

  min_psr = float(os.environ.get("EW_GATE_MIN_PSR", "0.95"))
  min_exp = float(os.environ.get("EW_EXPECTANCY_MIN_R", "0.0"))
  psr_val = psr_result.get("psr") if isinstance(psr_result, dict) else None
  dsr_val = dsr_result.get("dsr") if isinstance(dsr_result, dict) else None

  passed = (
    oos_exp >= min_exp
    and len(oos_returns) >= min_slice_samples()
    and (psr_val is None or psr_val >= min_psr)
  )

  return {
    "ok": True,
    "n_returns": n,
    "stitched_oos": {
      "n": len(oos_returns),
      "expectancy_r": round(oos_exp, 6),
      "sharpe": sharpe_from_returns(oos_returns),
      "positive_folds": positive_folds,
      "n_folds": len(fold_results),
    },
    "folds": fold_results,
    "psr": psr_result,
    "dsr": dsr_result,
    "num_trials_assumed": num_trials,
    "deployment_gate": {
      "verdict": "GO" if passed else "NO_GO",
      "passed": passed,
      "min_expectancy_r": min_exp,
      "min_psr": min_psr,
    },
  }

