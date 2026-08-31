"""vectorbt parameter sweeps on filter policies."""

from __future__ import annotations

import os
from itertools import product
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from engine.profit_lab.setup_returns import load_closed_setups, net_r_from_setup, setups_to_returns_frame


def _filter_setups(
  closed: List[dict],
  *,
  blocked_tfs: Set[str],
  blocked_dirs: Set[str],
  min_stop_pct: float,
) -> List[dict]:
  out = []
  for s in closed:
    tf = str(s.get("timeframe") or "")
    direction = str(s.get("direction") or "").upper()
    if tf in blocked_tfs:
      continue
    if direction in blocked_dirs:
      continue
    try:
      wae = float(s["wae"])
      stop = float(s["stop_loss"])
    except (KeyError, TypeError, ValueError):
      continue
    if wae <= 0:
      continue
    stop_pct = abs(wae - stop) / wae
    if stop_pct < min_stop_pct:
      continue
    out.append(s)
  return out


def run_vectorbt_sweep(
  *,
  max_combos: int = 200,
) -> Dict[str, Any]:
  """
  Sweep blocked TF sets × min stop distance × directions.
  Ranks by fee-adjusted expectancy using vectorbt portfolio metrics when available.
  """
  closed = load_closed_setups(apply_policy=False)
  if len(closed) < 30:
    return {"ok": False, "reason": "insufficient_closed", "n": len(closed)}

  all_tfs = sorted({str(s.get("timeframe") or "") for s in closed if s.get("timeframe")})
  weak_default = {"4h", "1d", "1w", "12h"}
  min_stop_grid = [0.005, 0.01, 0.015, 0.02, 0.03]
  tf_block_options = [
    set(),
    weak_default,
    weak_default | {"1h"},
    set(all_tfs) - {"15m"},
  ]
  dir_options = [set(), {"LONG"}]

  combos: List[Dict[str, Any]] = []
  for blocked_tfs, blocked_dirs, min_stop in product(tf_block_options, dir_options, min_stop_grid):
    filtered = _filter_setups(closed, blocked_tfs=blocked_tfs, blocked_dirs=blocked_dirs, min_stop_pct=min_stop)
    rets = [r for s in filtered if (r := net_r_from_setup(s)) is not None]
    if len(rets) < 30:
      continue
    exp = sum(rets) / len(rets)
    wr = sum(1 for r in rets if r > 0) / len(rets)
    combos.append({
      "blocked_tfs": sorted(blocked_tfs),
      "blocked_directions": sorted(blocked_dirs),
      "min_stop_pct": min_stop,
      "n": len(rets),
      "expectancy_r": round(exp, 6),
      "win_rate": round(wr, 4),
      "total_r": round(sum(rets), 4),
    })
    if len(combos) >= max_combos:
      break

  if not combos:
    return {"ok": False, "reason": "no_valid_combos"}

  combos.sort(key=lambda x: (x["expectancy_r"], x["n"]), reverse=True)
  best = combos[0]

  # vectorbt portfolio metrics on best combo
  vbt_metrics: Dict[str, Any] = {}
  try:
    import vectorbt as vbt

    risk_pct = float(os.environ.get("EW_ACCOUNT_RISK_PCT", "0.75")) / 100.0
    pct_rets = pd.Series([r * risk_pct for r in [
      net_r_from_setup(s) for s in _filter_setups(
        closed,
        blocked_tfs=set(best["blocked_tfs"]),
        blocked_dirs=set(best["blocked_directions"]),
        min_stop_pct=best["min_stop_pct"],
      )
      if net_r_from_setup(s) is not None
    ]])
    pf = vbt.Portfolio.from_returns(pct_rets, init_cash=50_000.0)
    vbt_metrics = {
      "total_return_pct": round(float(pf.total_return()) * 100, 4),
      "sharpe": round(float(pf.sharpe_ratio()), 4) if pf.sharpe_ratio() is not None else None,
      "max_drawdown_pct": round(float(pf.max_drawdown()) * 100, 4),
      "win_rate": round(float(pf.trades.win_rate()), 4) if hasattr(pf, "trades") else None,
    }
  except Exception as exc:
    vbt_metrics = {"error": str(exc)}

  return {
    "ok": True,
    "combos_evaluated": len(combos),
    "best": best,
    "best_vbt": vbt_metrics,
    "top_5": combos[:5],
    "recommended_env": {
      "EW_BLOCKED_TFS": ",".join(best["blocked_tfs"]) if best["blocked_tfs"] else "",
      "EW_BLOCKED_DIRECTIONS": ",".join(best["blocked_directions"]) if best["blocked_directions"] else "",
      "EW_MIN_STOP_PCT": str(best["min_stop_pct"]),
    },
  }
