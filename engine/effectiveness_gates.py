"""GO/NO-GO deployment gates — institutional validation (PSR, Wilson CI, regime gates)."""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _norm_cdf(x: float) -> float:
  return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def gate_thresholds() -> Dict[str, float]:
  """Pre-committed promotion thresholds (AlgoXpert / institutional WFA style)."""
  return {
    "min_trades_moderate": float(os.environ.get("EW_GATE_MIN_TRADES", "250")),
    "min_trades_weak": float(os.environ.get("EW_GATE_MIN_TRADES_WEAK", "100")),
    "min_sharpe": float(os.environ.get("EW_GATE_MIN_SHARPE", "0.5")),
    "min_profit_factor": float(os.environ.get("EW_GATE_MIN_PF", "1.1")),
    "max_drawdown_pct": float(os.environ.get("EW_GATE_MAX_DD_PCT", "15.0")),
    "min_win_rate": float(os.environ.get("EW_GATE_MIN_WIN_RATE", "0.45")),
    "min_psr": float(os.environ.get("EW_GATE_MIN_PSR", "0.95")),
    "min_tf_win_rate": float(os.environ.get("EW_GATE_MIN_TF_WIN_RATE", "0.40")),
    "min_tf_samples": float(os.environ.get("EW_GATE_MIN_TF_SAMPLES", "30")),
  }


def wilson_ci(wins: int, n: int, z: float = 1.96) -> Tuple[Optional[float], Optional[float]]:
  """Wilson score interval for binomial win rate."""
  if n <= 0:
    return None, None
  p = wins / n
  denom = 1 + z * z / n
  center = (p + z * z / (2 * n)) / denom
  margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
  return round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)


def probabilistic_sharpe_ratio(
  returns: Sequence[float],
  benchmark_sr: float = 0.0,
) -> Dict[str, Any]:
  """
  Lopez de Prado (2012) PSR — probability true Sharpe exceeds benchmark.
  Adjusts for sample size, skewness, and excess kurtosis.
  """
  n = len(returns)
  if n < 2:
    return {"psr": None, "n": n, "observed_sharpe": None, "mtrl": None}

  mean = sum(returns) / n
  var = sum((r - mean) ** 2 for r in returns) / (n - 1)
  std = math.sqrt(var) if var > 0 else 0.0
  if std <= 1e-12:
    return {"psr": 0.0, "n": n, "observed_sharpe": 0.0, "mtrl": None}

  sr = mean / std
  skew = sum((r - mean) ** 3 for r in returns) / (n * std ** 3) if n > 2 else 0.0
  kurt = sum((r - mean) ** 4 for r in returns) / (n * std ** 4) if n > 2 else 3.0
  excess_kurt = kurt - 3.0

  denom = math.sqrt(1 - skew * sr + (excess_kurt) / 4.0 * sr * sr)
  if denom <= 1e-12:
    denom = 1.0
  z = (sr - benchmark_sr) * math.sqrt(n - 1) / denom
  psr = _norm_cdf(z)

  # Minimum track record length for 95% significance at observed SR
  mtrl = None
  if sr > benchmark_sr and abs(sr) > 1e-6:
    target_z = 1.96
    mtrl = int(math.ceil((target_z * denom / (sr - benchmark_sr)) ** 2 + 1))

  return {
    "psr": round(psr, 4),
    "n": n,
    "observed_sharpe": round(sr, 4),
    "skew": round(skew, 4),
    "excess_kurtosis": round(excess_kurt, 4),
    "mtrl": mtrl,
  }


def deflated_sharpe_ratio(
  observed_sr: float,
  n: int,
  num_trials: int = 1,
  skew: float = 0.0,
  excess_kurt: float = 0.0,
) -> Dict[str, Any]:
  """
  Approximate deflated Sharpe — penalizes for multiple testing (Bailey & Lopez de Prado).
  """
  if n < 2 or num_trials < 1:
    return {"dsr": None, "num_trials": num_trials}
  euler_gamma = 0.5772156649
  expected_max_sr = math.sqrt(2 * math.log(num_trials)) if num_trials > 1 else 0.0
  expected_max_sr -= (math.log(math.pi) + euler_gamma) / (2 * math.sqrt(2 * math.log(num_trials))) if num_trials > 1 else 0.0
  benchmark = expected_max_sr / math.sqrt(n) if n > 0 else 0.0
  denom = math.sqrt(1 - skew * observed_sr + excess_kurt / 4.0 * observed_sr ** 2) if abs(observed_sr) > 1e-12 else 1.0
  z = (observed_sr - benchmark) * math.sqrt(n - 1) / max(denom, 1e-12)
  return {
    "dsr": round(_norm_cdf(z), 4),
    "benchmark_sr": round(benchmark, 4),
    "expected_max_sr": round(expected_max_sr, 4),
    "num_trials": num_trials,
  }


def max_drawdown_pct(equity_curve: Sequence[float]) -> Optional[float]:
  if len(equity_curve) < 2:
    return None
  peak = equity_curve[0]
  max_dd = 0.0
  for eq in equity_curve:
    if eq > peak:
      peak = eq
    if peak > 0:
      dd = (peak - eq) / peak * 100.0
      max_dd = max(max_dd, dd)
  return round(max_dd, 2)


def evaluate_gate(
  *,
  n_trades: int,
  win_rate: Optional[float],
  sharpe: Optional[float],
  profit_factor: Optional[float],
  return_pct: Optional[float],
  max_dd_pct: Optional[float],
  returns: Optional[Sequence[float]] = None,
  num_trials: int = 1,
  wins: Optional[int] = None,
) -> Dict[str, Any]:
  """Sequential GO/NO-GO gate evaluation."""
  th = gate_thresholds()
  gates: List[Dict[str, Any]] = []
  passed_all = True

  def _gate(name: str, passed: bool, detail: str, value: Any = None) -> None:
    nonlocal passed_all
    if not passed:
      passed_all = False
    gates.append({"gate": name, "passed": passed, "detail": detail, "value": value})

  # Gate 1: minimum sample size
  if n_trades >= th["min_trades_moderate"]:
    _gate("min_trades", True, f"n={n_trades} >= {th['min_trades_moderate']:.0f} (moderate reliability)", n_trades)
  elif n_trades >= th["min_trades_weak"]:
    _gate("min_trades", False, f"n={n_trades} weakly reliable (< {th['min_trades_moderate']:.0f})", n_trades)
  else:
    _gate("min_trades", False, f"n={n_trades} insufficient (< {th['min_trades_weak']:.0f})", n_trades)

  # Gate 2: win rate + Wilson CI lower bound
  if win_rate is not None and wins is not None and n_trades > 0:
    lo, hi = wilson_ci(wins, n_trades)
    wr_ok = win_rate >= th["min_win_rate"] and (lo is None or lo >= th["min_win_rate"] - 0.05)
    _gate(
      "win_rate",
      wr_ok,
      f"WR={win_rate:.1%} CI=[{lo},{hi}] (min {th['min_win_rate']:.0%})",
      win_rate,
    )
  elif win_rate is not None:
    _gate("win_rate", win_rate >= th["min_win_rate"], f"WR={win_rate:.1%}", win_rate)
  else:
    _gate("win_rate", False, "no win rate data")

  # Gate 3: risk-adjusted return
  if sharpe is not None:
    _gate("sharpe", sharpe >= th["min_sharpe"], f"Sharpe={sharpe:.2f} (min {th['min_sharpe']})", sharpe)
  else:
    _gate("sharpe", False, "no Sharpe computed")

  # Gate 4: profit factor
  if profit_factor is not None:
    _gate("profit_factor", profit_factor >= th["min_profit_factor"], f"PF={profit_factor:.2f}", profit_factor)
  else:
    _gate("profit_factor", False, "no profit factor")

  # Gate 5: drawdown
  if max_dd_pct is not None:
    _gate("max_drawdown", max_dd_pct <= th["max_drawdown_pct"], f"DD={max_dd_pct:.1f}%", max_dd_pct)
  else:
    _gate("max_drawdown", False, "no drawdown computed")

  # Gate 6: probabilistic Sharpe
  psr_result: Dict[str, Any] = {}
  if returns and len(returns) >= 2:
    psr_result = probabilistic_sharpe_ratio(returns)
    psr = psr_result.get("psr")
    if psr is not None:
      _gate("psr", psr >= th["min_psr"], f"PSR={psr:.2f} (min {th['min_psr']})", psr)
    dsr = deflated_sharpe_ratio(
      psr_result.get("observed_sharpe") or 0.0,
      len(returns),
      num_trials=num_trials,
      skew=psr_result.get("skew") or 0.0,
      excess_kurt=psr_result.get("excess_kurtosis") or 0.0,
    )
    psr_result["dsr"] = dsr
  else:
    _gate("psr", False, "insufficient return series for PSR")

  verdict = "GO" if passed_all else "NO_GO"
  if n_trades < th["min_trades_weak"]:
    verdict = "INSUFFICIENT_DATA"

  return {
    "verdict": verdict,
    "passed": passed_all,
    "gates": gates,
    "thresholds": th,
    "psr": psr_result,
    "n_trades": n_trades,
    "return_pct": return_pct,
  }


def evaluate_regime_gates(metrics: dict) -> Dict[str, Any]:
  """Per-timeframe regime gates — penalize weak TFs (e.g. 1d at 39.8% WR)."""
  th = gate_thresholds()
  by_tf = metrics.get("by_timeframe") or {}
  regimes: List[Dict[str, Any]] = []
  weak_tfs: List[str] = []
  strong_tfs: List[str] = []

  for tf, bucket in sorted(by_tf.items()):
    decided = int(bucket.get("decided") or 0)
    wr = bucket.get("win_rate")
    if decided < th["min_tf_samples"]:
      regimes.append({"timeframe": tf, "status": "insufficient", "n": decided, "win_rate": wr})
      continue
    if wr is not None and wr < th["min_tf_win_rate"]:
      weak_tfs.append(tf)
      regimes.append({"timeframe": tf, "status": "weak", "n": decided, "win_rate": wr})
    elif wr is not None and wr >= 0.55:
      strong_tfs.append(tf)
      regimes.append({"timeframe": tf, "status": "strong", "n": decided, "win_rate": wr})
    else:
      regimes.append({"timeframe": tf, "status": "neutral", "n": decided, "win_rate": wr})

  return {
    "regimes": regimes,
    "weak_timeframes": weak_tfs,
    "strong_timeframes": strong_tfs,
    "regime_gate_passed": len(weak_tfs) == 0,
  }
