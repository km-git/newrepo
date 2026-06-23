"""
Smart Money Concepts — ported from open-source Pine (SM Radar / LuxAlgo MSB toolkit).

Detects BOS, CHoCH, Order Blocks, and Fair Value Gaps without requiring
strict Elliott 5-wave impulse validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from core.eq_liquidity import detect_eq_sweep


@dataclass
class OrderBlock:
  bar_idx: int
  top: float
  bot: float
  is_bull: bool
  mitigated: bool = False


@dataclass
class FairValueGap:
  bar_idx: int
  top: float
  bot: float
  is_bull: bool
  filled: bool = False


def _pivot_indices(series: pd.Series, left: int, right: int, mode: str) -> List[int]:
  vals = series.astype(float).values
  n = len(vals)
  out: List[int] = []
  for i in range(left, n - right):
    window = vals[i - left : i + right + 1]
    if mode == "high" and vals[i] == np.nanmax(window):
      out.append(i)
    elif mode == "low" and vals[i] == np.nanmin(window):
      out.append(i)
  return out


def analyze_smc(
  df: pd.DataFrame,
  pivot_len: int = 5,
  ms_pivot_len: int = 7,
  ob_max_age: int = 80,
  fvg_max_age: int = 60,
) -> dict:
  """
  Run SMC analysis on OHLCV. Returns current structure state at last bar.
  Logic aligned with CedInvest/sm-radar-pine (MPL-2.0).
  """
  if df is None or len(df) < ms_pivot_len * 2 + 10:
    return {"status": "insufficient_data", "smc_valid": False, "smc_score": 0}

  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  close = df["Close"].astype(float)
  open_ = df["Open"].astype(float) if "Open" in df.columns else close.shift(1).fillna(close)
  n = len(df)
  price = float(close.iloc[-1])

  ph_idx = _pivot_indices(high, pivot_len, pivot_len, "high")
  pl_idx = _pivot_indices(low, pivot_len, pivot_len, "low")
  ph_ms = _pivot_indices(high, ms_pivot_len, ms_pivot_len, "high")
  pl_ms = _pivot_indices(low, ms_pivot_len, ms_pivot_len, "low")

  last_swing_high = float(high.iloc[ph_idx[-1]]) if ph_idx else None
  last_swing_low = float(low.iloc[pl_idx[-1]]) if pl_idx else None
  last_ph_ms = float(high.iloc[ph_ms[-1]]) if ph_ms else None
  last_pl_ms = float(low.iloc[pl_ms[-1]]) if pl_ms else None

  c0, c1 = float(close.iloc[-1]), float(close.iloc[-2])
  bos_bull = last_swing_high is not None and c0 > last_swing_high and c1 <= last_swing_high
  bos_bear = last_swing_low is not None and c0 < last_swing_low and c1 >= last_swing_low

  # Market structure trend from MS pivots (walk recent breaks)
  trend = 0
  last_event = "none"
  for i in range(max(0, n - 120), n):
    if not ph_ms:
      break
    for pi in ph_ms:
      if pi >= i:
        continue
      lvl = float(high.iloc[pi])
      if float(close.iloc[i]) > lvl and float(close.iloc[i - 1]) <= lvl:
        last_event = "choch_bull" if trend == -1 else "bos_bull"
        trend = 1
    for pi in pl_ms:
      if pi >= i:
        continue
      lvl = float(low.iloc[pi])
      if float(close.iloc[i]) < lvl and float(close.iloc[i - 1]) >= lvl:
        last_event = "choch_bear" if trend == 1 else "bos_bear"
        trend = -1

  ms_bull = last_event in ("bos_bull", "choch_bull")
  ms_bear = last_event in ("bos_bear", "choch_bear")

  # Order blocks from recent BOS (last 80 bars)
  obs: List[OrderBlock] = []
  start = max(0, n - ob_max_age - 20)
  for i in range(start, n):
    if i < 2:
      continue
    sh = None
    sl = None
    for pi in ph_idx:
      if pi < i:
        sh = float(high.iloc[pi])
    for pi in pl_idx:
      if pi < i:
        sl = float(low.iloc[pi])
    ci, ci1 = float(close.iloc[i]), float(close.iloc[i - 1])
    if sh and ci > sh and ci1 <= sh:
      for j in range(1, min(50, i)):
        idx = i - j
        if float(close.iloc[idx]) < float(open_.iloc[idx]):
          obs.append(OrderBlock(idx, float(high.iloc[idx]), float(low.iloc[idx]), True))
          break
    if sl and ci < sl and ci1 >= sl:
      for j in range(1, min(50, i)):
        idx = i - j
        if float(close.iloc[idx]) > float(open_.iloc[idx]):
          obs.append(OrderBlock(idx, float(high.iloc[idx]), float(low.iloc[idx]), False))
          break

  active_obs: List[dict] = []
  for ob in obs[-12:]:
    if n - 1 - ob.bar_idx > ob_max_age:
      continue
    touched = (price <= ob.top and price >= ob.bot) if ob.is_bull else (price >= ob.bot and price <= ob.top)
    active_obs.append({
      "top": ob.top, "bot": ob.bot, "is_bull": ob.is_bull,
      "in_zone": touched, "age_bars": n - 1 - ob.bar_idx,
    })

  # FVG detection
  fvgs: List[FairValueGap] = []
  for i in range(3, n):
    if float(low.iloc[i - 1]) > float(high.iloc[i - 3]):
      fvgs.append(FairValueGap(i - 2, float(low.iloc[i - 1]), float(high.iloc[i - 3]), True))
    if float(high.iloc[i - 1]) < float(low.iloc[i - 3]):
      fvgs.append(FairValueGap(i - 2, float(low.iloc[i - 3]), float(high.iloc[i - 1]), False))

  active_fvgs: List[dict] = []
  for f in fvgs[-20:]:
    if n - 1 - f.bar_idx > fvg_max_age:
      continue
    in_gap = f.bot <= price <= f.top
    active_fvgs.append({
      "top": f.top, "bot": f.bot, "is_bull": f.is_bull,
      "in_gap": in_gap, "age_bars": n - 1 - f.bar_idx,
    })

  in_bull_ob = any(o["in_zone"] and o["is_bull"] for o in active_obs)
  in_bear_ob = any(o["in_zone"] and not o["is_bull"] for o in active_obs)
  in_bull_fvg = any(f["in_gap"] and f["is_bull"] for f in active_fvgs)
  in_bear_fvg = any(f["in_gap"] and not f["is_bull"] for f in active_fvgs)

  structure_bias = "BULL" if trend == 1 else "BEAR" if trend == -1 else "NEUTRAL"
  smc_score = 0
  tags: List[str] = []

  if ms_bull or bos_bull:
    smc_score += 22
    tags.append("SMC BOS bull" if "bos" in last_event else "SMC CHoCH bull")
  if ms_bear or bos_bear:
    smc_score += 22
    tags.append("SMC BOS bear" if "bos" in last_event else "SMC CHoCH bear")
  if in_bull_ob:
    smc_score += 18
    tags.append("in bullish OB")
  if in_bear_ob:
    smc_score += 18
    tags.append("in bearish OB")
  if in_bull_fvg:
    smc_score += 12
    tags.append("bullish FVG zone")
  if in_bear_fvg:
    smc_score += 12
    tags.append("bearish FVG zone")

  smc_valid = smc_score >= 40 and structure_bias != "NEUTRAL"
  smc_partial = smc_score >= 25

  eq_sweep = None
  if structure_bias in ("BULL", "BEAR"):
    eq_sweep = detect_eq_sweep(df, "LONG" if structure_bias == "BULL" else "SHORT")
  if eq_sweep:
    smc_score += 18
    tags.append(eq_sweep.get("tag", "liquidity sweep"))
    smc_partial = True
    if smc_score >= 35:
      smc_valid = structure_bias != "NEUTRAL"

  return {
    "status": "ok",
    "structure_bias": structure_bias,
    "last_event": last_event,
    "trend": trend,
    "bos_bull": bos_bull,
    "bos_bear": bos_bear,
    "in_bull_ob": in_bull_ob,
    "in_bear_ob": in_bear_ob,
    "in_bull_fvg": in_bull_fvg,
    "in_bear_fvg": in_bear_fvg,
    "active_obs": len(active_obs),
    "active_fvgs": len(active_fvgs),
    "smc_score": min(100, smc_score),
    "smc_valid": smc_valid,
    "smc_partial": smc_partial,
    "tags": tags,
    "eq_sweep": eq_sweep,
    "ms_levels": {"swing_high": last_ph_ms, "swing_low": last_pl_ms},
  }


def smc_aligns_direction(smc: dict, direction: str) -> bool:
  if not smc or smc.get("status") != "ok":
    return False
  is_long = direction in ("LONG", "BULL")
  bias = smc.get("structure_bias", "NEUTRAL")
  if is_long:
    return bias == "BULL" or smc.get("in_bull_ob") or smc.get("in_bull_fvg")
  return bias == "BEAR" or smc.get("in_bear_ob") or smc.get("in_bear_fvg")
