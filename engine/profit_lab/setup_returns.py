"""Chronological fee-adjusted R-multiples from tracked closed setups."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd


def _parse_ts(value: str) -> float:
  if not value:
    return 0.0
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
  except (TypeError, ValueError):
    return 0.0


def _tp1_partial(setup: dict) -> float:
  return float(setup.get("tp1_exit_pct") or os.environ.get("EW_TP1_EXIT_PCT", "50")) / 100.0


def net_r_from_setup(setup: dict, *, fee: Optional[float] = None) -> Optional[float]:
  """Gross geometry R minus round-trip fee drag in R units."""
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
  if risk <= 0 or wae <= 0:
    return None
  if fee is None:
    try:
      from engine.paper_simulator import fee_rate

      fee = fee_rate()
    except Exception:
      fee = float(os.environ.get("EW_PAPER_FEE_RATE", "0.0026"))
  stop_dist_pct = risk / wae
  fee_drag_r = (2.0 * fee) / stop_dist_pct if stop_dist_pct > 0 else 0.0
  partial = _tp1_partial(setup)
  if st == "sl_hit":
    return -1.0 - fee_drag_r
  reward_r = abs(tp1 - wae) / risk
  return reward_r * partial - fee_drag_r


def load_closed_setups(*, apply_policy: bool = True) -> List[dict]:
  from engine.outcome_tracker import _dedupe_closed, _load_state

  state = _load_state()
  closed = _dedupe_closed([
    s for s in state.get("closed", [])
    if s.get("status") in ("tp1_hit", "sl_hit")
  ])
  if apply_policy and os.environ.get("EW_TRACKED_USE_POLICY", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.execution_gates import filter_closed_for_policy

      closed = filter_closed_for_policy(closed)
    except Exception:
      pass
  return closed


def setups_to_returns_frame(
  closed: Optional[Sequence[dict]] = None,
  *,
  apply_policy: bool = True,
) -> pd.DataFrame:
  """DataFrame: ts, net_r, tf, direction, symbol, pair_tf, setup_id."""
  closed = list(closed) if closed is not None else load_closed_setups(apply_policy=apply_policy)
  rows: List[Dict[str, Any]] = []
  for s in closed:
    net_r = net_r_from_setup(s)
    if net_r is None:
      continue
    ts_raw = s.get("resolved_at") or s.get("recorded_at") or ""
    ts = _parse_ts(str(ts_raw))
    sym = str(s.get("symbol") or "")
    tf = str(s.get("timeframe") or "")
    direction = str(s.get("direction") or "").upper()
    rows.append({
      "ts": ts,
      "resolved_at": ts_raw,
      "net_r": net_r,
      "timeframe": tf,
      "direction": direction,
      "symbol": sym,
      "pair_tf": f"{sym}|{tf}",
      "setup_id": s.get("id") or f"{sym}|{tf}|{direction}",
      "status": s.get("status"),
    })
  if not rows:
    return pd.DataFrame(columns=[
      "ts", "resolved_at", "net_r", "timeframe", "direction", "symbol", "pair_tf", "setup_id", "status",
    ])
  df = pd.DataFrame(rows)
  df = df.sort_values("ts").reset_index(drop=True)
  df["datetime"] = pd.to_datetime(df["ts"], unit="s", utc=True)
  return df


def equity_curve_from_returns(
  returns_r: Sequence[float],
  *,
  equity_start: float = 50_000.0,
  risk_pct: Optional[float] = None,
) -> List[float]:
  risk_pct = risk_pct if risk_pct is not None else float(os.environ.get("EW_ACCOUNT_RISK_PCT", "0.75")) / 100.0
  equity = equity_start
  curve = [equity]
  for r in returns_r:
    equity *= 1.0 + r * risk_pct
    curve.append(equity)
  return curve


def pct_returns_from_r(returns_r: Sequence[float], *, risk_pct: Optional[float] = None) -> pd.Series:
  risk_pct = risk_pct if risk_pct is not None else float(os.environ.get("EW_ACCOUNT_RISK_PCT", "0.75")) / 100.0
  return pd.Series([r * risk_pct for r in returns_r])


def slice_key(row: dict, dimensions: Tuple[str, ...]) -> str:
  parts = []
  for dim in dimensions:
    if dim == "pair_tf":
      parts.append(str(row.get("pair_tf") or ""))
    elif dim == "timeframe":
      parts.append(str(row.get("timeframe") or ""))
    elif dim == "direction":
      parts.append(str(row.get("direction") or ""))
    else:
      parts.append(str(row.get(dim) or ""))
  return "|".join(parts)
