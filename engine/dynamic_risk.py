"""Dynamic risk management — vol regime, TV confluence, history, drawdown."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import pandas as pd


def dynamic_risk_enabled() -> bool:
  return os.environ.get("EW_DYNAMIC_RISK", "1").lower() not in ("0", "false", "no")


def atr_percentile(df: Optional[pd.DataFrame], lookback: int = 60) -> float:
  """Current ATR% vs recent distribution (0–100)."""
  if df is None or len(df) < lookback + 15:
    return 50.0
  from core.tv_indicators import atr_series

  atr = atr_series(df)
  close = df["Close"].astype(float)
  pct = (atr / close.replace(0, float("nan"))) * 100
  recent = pct.iloc[-lookback:].dropna()
  if len(recent) < 10:
    return 50.0
  current = float(pct.iloc[-1])
  return round(float((recent < current).sum() / len(recent) * 100), 1)


def compute_risk_multiplier(
  *,
  symbol: str = "",
  timeframe: str = "",
  direction: str = "",
  df: Optional[pd.DataFrame] = None,
  tv_score: Optional[int] = None,
  readiness_score: Optional[int] = None,
  hist_win_rate: Optional[float] = None,
  hist_n: int = 0,
  gtc_tier: str = "executable",
  honest_tier: str = "probe",
) -> Dict[str, Any]:
  """
  Continuous risk multiplier 0.25–1.25 applied to account risk %.

  Layers:
  1. Volatility regime (ATR percentile) — high vol shrinks size
  2. TV OSS confluence — misaligned trend shrinks, aligned grows slightly
  3. Historical win rate — poor history shrinks, strong grows
  4. Drawdown halt proximity — near threshold shrinks
  5. Readiness score — maps 0–100 to ±10%
  """
  if not dynamic_risk_enabled():
    return {"mult": 1.0, "enabled": False, "factors": []}

  mult = 1.0
  factors = []

  # Vol regime
  ap = atr_percentile(df)
  if ap >= 80:
    mult *= 0.70
    factors.append(f"vol_high p{ap:.0f} → ×0.70")
  elif ap >= 60:
    mult *= 0.85
    factors.append(f"vol_elevated p{ap:.0f} → ×0.85")
  elif ap <= 20:
    mult *= 1.05
    factors.append(f"vol_low p{ap:.0f} → ×1.05")

  # TV confluence
  if tv_score is not None:
    if tv_score >= 70:
      mult *= 1.10
      factors.append(f"tv_score {tv_score} → ×1.10")
    elif tv_score < 45:
      mult *= 0.75
      factors.append(f"tv_score {tv_score} weak → ×0.75")
    elif tv_score < 55:
      mult *= 0.90
      factors.append(f"tv_score {tv_score} neutral → ×0.90")

  # Historical feedback
  if hist_win_rate is not None and hist_n >= 3:
    if hist_win_rate < 0.40:
      mult *= 0.75
      factors.append(f"hist_wr {hist_win_rate:.0%} n={hist_n} → ×0.75")
    elif hist_win_rate > 0.55:
      mult *= 1.10
      factors.append(f"hist_wr {hist_win_rate:.0%} n={hist_n} → ×1.10")

  # Readiness
  if readiness_score is not None:
    if readiness_score >= 85:
      mult *= 1.05
      factors.append(f"readiness {readiness_score} → ×1.05")
    elif readiness_score < 55:
      mult *= 0.85
      factors.append(f"readiness {readiness_score} low → ×0.85")

  # Drawdown proximity
  try:
    from engine.risk_ops import _load, drawdown_threshold_pct

    state = _load()
    dd = float(state.get("drawdown_pct") or 0)
    threshold = drawdown_threshold_pct()
    if dd >= threshold * 0.7:
      mult *= 0.50
      factors.append(f"drawdown {dd:.1f}% near halt → ×0.50")
    elif dd >= threshold * 0.4:
      mult *= 0.75
      factors.append(f"drawdown {dd:.1f}% elevated → ×0.75")
  except Exception:
    pass

  # Probe tier cap
  if honest_tier == "probe":
    mult = min(mult, 0.85)
    factors.append("probe tier cap ≤0.85")

  if gtc_tier == "monitor":
    mult = min(mult, 0.50)

  mult = round(max(0.25, min(1.25, mult)), 3)
  return {
    "enabled": True,
    "mult": mult,
    "atr_percentile": ap,
    "factors": factors,
    "symbol": symbol,
    "timeframe": timeframe,
    "direction": direction,
  }


def apply_dynamic_account_risk(base_pct: float, risk_ctx: dict) -> float:
  mult = float(risk_ctx.get("mult") or 1.0)
  return round(base_pct * mult, 4)
