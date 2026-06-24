"""
Institutional edge stack — Phases 1–5 integrated.

Phase 1: smartmoneyconcepts (OB, FVG, liquidity sweeps, BOS/CHoCH)
Phase 2: CVD divergence from OHLCV
Phase 3: Rolling volume profile (POC, VAH, VAL)
Phase 4: Order book imbalance (OBI) via ccxt
Phase 5: Heikin Ashi + ROC (pandas-ta)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
  from smartmoneyconcepts import smc as smc_lib
  _HAS_SMC = True
except ImportError:
  _HAS_SMC = False

try:
  import pandas_ta as ta
  _HAS_TA = True
except ImportError:
  _HAS_TA = False

from core.smc_structure import analyze_smc as _fallback_smc
from core.eq_liquidity import detect_eq_sweep, detect_equal_levels
from core.msb_zscore import msb_allows_entry, validate_msb_zscore


def _prep_ohlc(df: pd.DataFrame) -> pd.DataFrame:
  """Normalize columns for smartmoneyconcepts (lowercase + volume)."""
  out = df.copy()
  colmap = {c: c.lower() for c in out.columns}
  out = out.rename(columns=colmap)
  if "volume" not in out.columns:
    out["volume"] = 1.0
  for c in ("open", "high", "low", "close"):
    if c not in out.columns:
      raise ValueError(f"missing column {c}")
  return out[["open", "high", "low", "close", "volume"]].astype(float)


def _swing_length(tf: str) -> int:
  return {"15m": 8, "1h": 12, "4h": 15, "1d": 20, "1w": 25}.get(tf, 12)


def _price_near_zone(price: float, top: float, bot: float, tol_pct: float = 0.005) -> bool:
  """Price inside zone or within tolerance (ICT retest entry)."""
  tol = price * tol_pct
  return bot - tol <= price <= top + tol


def _bar_touches_zone(bar_low: float, bar_high: float, top: float, bot: float) -> bool:
  return bar_low <= top and bar_high >= bot


def structure_blocks_entry(structure_event: Optional[str], direction: str) -> bool:
  """Hard block: bear structure on LONG / bull structure on SHORT (ledger anti-predictive)."""
  if not structure_event:
    return False
  is_long = direction in ("LONG", "BULL")
  if is_long and structure_event in ("choch_bear", "bos_bear"):
    return True
  if not is_long and structure_event in ("choch_bull", "bos_bull"):
    return True
  return False


def _zone_bounds(
  active_ob: Optional[dict],
  active_fvg: Optional[dict],
) -> Tuple[Optional[float], Optional[float]]:
  if active_ob:
    return float(active_ob["top"]), float(active_ob["bot"])
  if active_fvg:
    return float(active_fvg["top"]), float(active_fvg["bot"])
  return None, None


def detect_entry_confirmation(
  df: pd.DataFrame,
  direction: str,
  zone_top: Optional[float] = None,
  zone_bot: Optional[float] = None,
) -> dict:
  """
  SMC executable confirm: rejection wick at zone OR bar+2 directional close after touch.
  """
  if df is None or len(df) < 4:
    return {"confirmed": False, "mode": None}
  is_long = direction in ("LONG", "BULL")
  o = df["Open"].astype(float)
  h = df["High"].astype(float)
  l = df["Low"].astype(float)
  c = df["Close"].astype(float)

  zt = zb = None
  touch_pad = float(c.iloc[-1]) * 0.006
  if zone_top is not None and zone_bot is not None:
    zt, zb = max(zone_top, zone_bot), min(zone_top, zone_bot)
    touch_pad = max((zt - zb) * 0.25, zt * 0.006)

  def _touched(bar_l: float, bar_h: float) -> bool:
    if zt is None:
      return True
    return bar_l <= zt + touch_pad and bar_h >= zb - touch_pad

  for i in range(-3, 0):
    bar_o, bar_h, bar_l, bar_c = float(o.iloc[i]), float(h.iloc[i]), float(l.iloc[i]), float(c.iloc[i])
    rng = bar_h - bar_l
    if rng <= 0 or not _touched(bar_l, bar_h):
      continue
    if is_long:
      lower_wick = min(bar_o, bar_c) - bar_l
      if lower_wick / rng >= 0.35 and bar_c >= bar_o:
        return {"confirmed": True, "mode": "rejection_wick"}
    else:
      upper_wick = bar_h - max(bar_o, bar_c)
      if upper_wick / rng >= 0.35 and bar_c <= bar_o:
        return {"confirmed": True, "mode": "rejection_wick"}

  if zt is not None and len(df) >= 4:
    touch_idx = None
    for i in range(-4, -1):
      if _touched(float(l.iloc[i]), float(h.iloc[i])):
        touch_idx = i
        break
    if touch_idx is not None:
      c_touch = float(c.iloc[touch_idx])
      c_last = float(c.iloc[-1])
      if is_long and c_last > c_touch:
        return {"confirmed": True, "mode": "bar+2"}
      if not is_long and c_last < c_touch:
        return {"confirmed": True, "mode": "bar+2"}

  return {"confirmed": False, "mode": None}


def _is_chop_market(df: pd.DataFrame, period: int = 20) -> bool:
  """Low-trend chop — soften VP hard filter."""
  if df is None or len(df) < period + 5:
    return False
  high = df["High"].astype(float).tail(period)
  low = df["Low"].astype(float).tail(period)
  close = df["Close"].astype(float).tail(period)
  rng = float(high.max() - low.min())
  atr_proxy = float((high - low).rolling(14).mean().iloc[-1])
  if atr_proxy <= 0:
    return False
  return rng / atr_proxy < 3.5 and abs(float(close.iloc[-1] / close.iloc[0] - 1)) < 0.02


def detect_session_liquidity(df: pd.DataFrame) -> dict:
  """Session liquidity windows (UTC) — Asia / London / NY kill zones."""
  if df is None or len(df) < 5:
    return {"status": "insufficient_data"}
  idx = df.index[-1]
  hour = getattr(idx, "hour", None)
  if hour is None:
    return {"status": "no_timestamp"}
  if 0 <= hour < 8:
    session, tag = "asia", "asia_liquidity"
  elif 8 <= hour < 13:
    session, tag = "london", "london_open"
  elif 13 <= hour < 17:
    session, tag = "london_ny", "london_ny_overlap"
  elif 17 <= hour < 22:
    session, tag = "ny", "ny_session"
  else:
    session, tag = "off_hours", "off_hours"
  return {"status": "ok", "session": session, "tag": tag, "hour_utc": hour}


def run_smc_library(df: pd.DataFrame, tf: str = "1h") -> dict:
  """Phase 1 — smartmoneyconcepts detection."""
  if not _HAS_SMC or df is None or len(df) < 60:
    return {"status": "unavailable", "source": "fallback"}

  try:
    ohlc = _prep_ohlc(df)
    sl = _swing_length(tf)
    swing = smc_lib.swing_highs_lows(ohlc, swing_length=sl)
    ob = smc_lib.ob(ohlc, swing)
    fvg = smc_lib.fvg(ohlc)
    liq = smc_lib.liquidity(ohlc, swing, range_percent=0.01)
    bc = smc_lib.bos_choch(ohlc, swing)

    price = float(ohlc["close"].iloc[-1])
    n = len(ohlc)

    touch_lb = {"15m": 24, "1h": 20, "4h": 16}.get(tf, 20)
    window = ohlc.tail(touch_lb)

    def _ob_signal(direction: str) -> Optional[dict]:
      rows = ob.dropna(subset=["OB"]).tail(30)
      for i in range(len(rows) - 1, -1, -1):
        row = rows.iloc[i]
        is_bull = row["OB"] == 1
        if direction == "LONG" and not is_bull:
          continue
        if direction == "SHORT" and is_bull:
          continue
        top, bot = float(row["Top"]), float(row["Bottom"])
        if _price_near_zone(price, top, bot):
          return {
            "top": top, "bot": bot, "is_bull": is_bull,
            "strength": float(row.get("Percentage", 0)), "mode": "active",
          }
        for _, bar in window.iterrows():
          if _bar_touches_zone(float(bar["low"]), float(bar["high"]), top, bot):
            return {
              "top": top, "bot": bot, "is_bull": is_bull,
              "strength": float(row.get("Percentage", 0)), "mode": "recent_touch",
            }
      return None

    def _fvg_signal(direction: str) -> Optional[dict]:
      rows = fvg.dropna(subset=["FVG"]).tail(24)
      for i in range(len(rows) - 1, -1, -1):
        row = rows.iloc[i]
        is_bull = row["FVG"] == 1
        if direction == "LONG" and not is_bull:
          continue
        if direction == "SHORT" and is_bull:
          continue
        top, bot = float(row["Top"]), float(row["Bottom"])
        mit = row.get("MitigatedIndex", np.nan)
        if pd.notna(mit) and mit >= n - 2:
          continue
        if _price_near_zone(price, top, bot):
          return {"top": top, "bot": bot, "is_bull": is_bull, "mode": "active"}
        for _, bar in window.iterrows():
          if _bar_touches_zone(float(bar["low"]), float(bar["high"]), top, bot):
            return {"top": top, "bot": bot, "is_bull": is_bull, "mode": "recent_touch"}
      return None

    def _recent_sweep(direction: str, lookback: int = 50) -> Optional[dict]:
      tail = liq.dropna(subset=["Liquidity"]).tail(lookback)
      for i in range(len(tail) - 1, -1, -1):
        row = tail.iloc[i]
        swept = row.get("Swept", 0)
        if pd.isna(swept) or swept == 0:
          continue
        is_bull_liq = row["Liquidity"] == 1
        if direction == "LONG" and is_bull_liq:
          return {"level": float(row["Level"]), "swept_idx": int(swept)}
        if direction == "SHORT" and not is_bull_liq:
          return {"level": float(row["Level"]), "swept_idx": int(swept)}
      return None

    def _recent_structure(direction: str, lookback: int = 40) -> Tuple[Optional[str], int]:
      tail = bc.tail(lookback)
      for i in range(len(tail) - 1, -1, -1):
        row = tail.iloc[i]
        if pd.notna(row.get("CHOCH")) and row["CHOCH"] != 0:
          if direction == "LONG" and row["CHOCH"] == 1:
            return "choch_bull", 22
          if direction == "SHORT" and row["CHOCH"] == -1:
            return "choch_bear", 22
        if pd.notna(row.get("BOS")) and row["BOS"] != 0:
          if direction == "LONG" and row["BOS"] == 1:
            return "bos_bull", 18
          if direction == "SHORT" and row["BOS"] == -1:
            return "bos_bear", 18
      return None, 0

    return {
      "status": "ok",
      "source": "smartmoneyconcepts",
      "swing_length": sl,
      "ob": ob,
      "fvg": fvg,
      "liquidity": liq,
      "bos_choch": bc,
      "_helpers": {
        "active_ob": _ob_signal,
        "active_fvg": _fvg_signal,
        "recent_sweep": _recent_sweep,
        "recent_structure": _recent_structure,
      },
    }
  except Exception as e:
    return {"status": "error", "error": str(e), "source": "fallback"}


def compute_cvd(df: pd.DataFrame) -> pd.Series:
  """Phase 2 — cumulative volume delta from OHLCV."""
  ohlc = _prep_ohlc(df)
  close = ohlc["close"].values
  open_ = ohlc["open"].values
  vol = ohlc["volume"].values
  delta = np.where(close > open_, vol, np.where(close < open_, -vol, 0.0))
  return pd.Series(delta, index=df.index).cumsum()


def detect_cvd_divergence(df: pd.DataFrame, lookback: int = 20) -> Optional[str]:
  """Price HH + CVD LH = bearish; price LL + CVD HL = bullish."""
  if df is None or len(df) < lookback + 5:
    return None
  cvd = compute_cvd(df)
  close = df["Close"].astype(float) if "Close" in df.columns else df["close"].astype(float)
  seg_p = close.iloc[-lookback:]
  seg_c = cvd.iloc[-lookback:]
  p0, p1 = float(seg_p.iloc[0]), float(seg_p.iloc[-1])
  c0, c1 = float(seg_c.iloc[0]), float(seg_c.iloc[-1])
  if p1 < p0 and c1 > c0:
    return "cvd_bullish_divergence"
  if p1 > p0 and c1 < c0:
    return "cvd_bearish_divergence"
  return None


def compute_volume_profile(df: pd.DataFrame, period: int = 20) -> dict:
  """Phase 3 — rolling volume profile POC / VAH / VAL."""
  if df is None or len(df) < period + 5:
    return {"status": "insufficient_data"}
  ohlc = _prep_ohlc(df)
  window = ohlc.tail(period)
  tp = (window["high"] + window["low"] + window["close"]) / 3
  vol = window["volume"].replace(0, np.nan).fillna(1.0)
  bins = 24
  lo, hi = float(window["low"].min()), float(window["high"].max())
  if hi <= lo:
    return {"status": "flat"}
  edges = np.linspace(lo, hi, bins + 1)
  hist = np.zeros(bins)
  for t, v in zip(tp.values, vol.values):
    idx = min(bins - 1, int((t - lo) / (hi - lo + 1e-12) * bins))
    hist[idx] += v
  poc_idx = int(np.argmax(hist))
  poc = (edges[poc_idx] + edges[poc_idx + 1]) / 2
  total = hist.sum()
  target = total * 0.70
  order = np.argsort(hist)[::-1]
  cum = 0.0
  used = set()
  for i in order:
    cum += hist[i]
    used.add(i)
    if cum >= target:
      break
  used_idx = sorted(used)
  val = edges[used_idx[0]]
  vah = edges[used_idx[-1] + 1]
  price = float(ohlc["close"].iloc[-1])
  return {
    "status": "ok",
    "poc": round(poc, 6),
    "vah": round(vah, 6),
    "val": round(val, 6),
    "above_val": price > val,
    "below_vah": price < vah,
    "near_poc": abs(price - poc) / price * 100 < 0.5,
    "period": period,
  }


def compute_ha_roc(df: pd.DataFrame, roc_period: int = 9) -> dict:
  """Phase 5 — Heikin Ashi trend + ROC momentum."""
  if df is None or len(df) < roc_period + 5:
    return {"status": "insufficient_data"}
  ohlc = _prep_ohlc(df)
  if _HAS_TA:
    ha = ta.ha(ohlc["open"], ohlc["high"], ohlc["low"], ohlc["close"])
    if ha is not None and len(ha.columns) >= 4:
      ha_close = ha.iloc[:, 3]
      ha_open = ha.iloc[:, 0]
      ha_bull = bool(ha_close.iloc[-1] > ha_open.iloc[-1])
      ha_bear = bool(ha_close.iloc[-1] < ha_open.iloc[-1])
    else:
      ha_bull = ha_bear = False
    roc = ta.roc(ohlc["close"], length=roc_period)
    roc_val = float(roc.iloc[-1]) if roc is not None and pd.notna(roc.iloc[-1]) else 0.0
  else:
    close = ohlc["close"]
    roc_val = float((close.iloc[-1] / close.iloc[-roc_period] - 1) * 100)
    ha_bull = close.iloc[-1] > close.iloc[-3]
    ha_bear = close.iloc[-1] < close.iloc[-3]
  return {
    "status": "ok",
    "ha_bull": ha_bull,
    "ha_bear": ha_bear,
    "roc": round(roc_val, 3),
    "roc_positive": roc_val > 0,
    "roc_negative": roc_val < 0,
  }


def compute_obi(exchange, symbol: str, depth: int = 20) -> dict:
  """Phase 4 — order book imbalance."""
  from core.market_tools import orderbook_imbalance
  if exchange is None:
    return {"available": False, "imbalance": 0.0}
  ob = orderbook_imbalance(exchange, symbol, depth=depth)
  if not ob.get("available"):
    return ob
  imb = float(ob.get("imbalance", 0))
  ob["obi_bullish"] = imb > 0.15
  ob["obi_bearish"] = imb < -0.15
  ob["obi_strong"] = abs(imb) > 0.25
  return ob


def analyze_institutional_tf(
  df: pd.DataFrame,
  tf: str,
  direction: str,
  exchange=None,
  symbol: str = "",
) -> dict:
  """Full institutional analysis for one timeframe."""
  is_long = direction in ("LONG", "BULL")
  dir_norm = "LONG" if is_long else "SHORT"

  smc = run_smc_library(df, tf)
  tags: List[str] = []
  score = 0

  active_ob = active_fvg = recent_sweep = eq_sweep = None
  structure_event = None
  msb = {"status": "no_break", "pass": False}

  if smc.get("status") == "ok":
    h = smc["_helpers"]
    active_ob = h["active_ob"](dir_norm)
    active_fvg = h["active_fvg"](dir_norm)
    recent_sweep = h["recent_sweep"](dir_norm)
    structure_event, struct_pts = h["recent_structure"](dir_norm)
    if structure_event:
      if structure_blocks_entry(structure_event, dir_norm):
        tags.append(f"SMC {structure_event.replace('_', ' ')} (counter-trend block)")
      else:
        score += struct_pts
        tags.append(f"SMC {structure_event.replace('_', ' ')}")
    if active_ob:
      score += 18
      tags.append("in bullish OB" if active_ob["is_bull"] else "in bearish OB")
    if active_fvg:
      score += 14
      tags.append("bullish FVG zone" if active_fvg["is_bull"] else "bearish FVG zone")
    if recent_sweep:
      score += 20
      tags.append("liquidity sweep")
  else:
    fb = _fallback_smc(df)
    if fb.get("status") == "ok":
      score += int(fb.get("smc_score", 0))
      tags.extend(fb.get("tags", []))
      if fb.get("eq_sweep"):
        recent_sweep = fb["eq_sweep"]
        score += 18
        tags.append(fb["eq_sweep"].get("tag", "liquidity sweep"))

  # EQH/EQL sweeps (explicit equal-level liquidity)
  eq_sweep = detect_eq_sweep(df, dir_norm)
  if eq_sweep and not recent_sweep:
    recent_sweep = eq_sweep
    score += 18
    tags.append(eq_sweep.get("tag", "liquidity sweep"))
  elif eq_sweep:
    score += 6
    if eq_sweep.get("type") == "eql":
      tags.append("equal lows")
    else:
      tags.append("equal highs")

  eq_levels = detect_equal_levels(df)
  if eq_levels.get("has_eqh"):
    tags.append("equal highs cluster")
  if eq_levels.get("has_eql"):
    tags.append("equal lows cluster")

  # LuxAlgo MSB z-score on structure break
  msb = validate_msb_zscore(df, dir_norm)
  if msb.get("status") == "ok":
    if msb.get("pass"):
      score += 4
      tags.append("MSB z-score pass")
    else:
      score -= 4
      tags.append("MSB z-score weak")

  cvd_div = detect_cvd_divergence(df)
  if cvd_div == "cvd_bullish_divergence" and is_long:
    score += 16
    tags.append("CVD bullish divergence")
  elif cvd_div == "cvd_bearish_divergence" and not is_long:
    score += 16
    tags.append("CVD bearish divergence")

  vp = compute_volume_profile(df)
  vp_filter_ok = True
  vp_soft_fail = False
  chop = _is_chop_market(df)
  if vp.get("status") == "ok":
    if is_long and not vp.get("above_val"):
      vp_soft_fail = True
    elif not is_long and not vp.get("below_vah"):
      vp_soft_fail = True
    if vp_soft_fail and chop:
      vp_filter_ok = True
      score -= 3
      tags.append("VP soft pass (chop)")
    elif vp_soft_fail:
      vp_filter_ok = False
    if vp.get("near_poc"):
      score += 8
      tags.append("at volume POC")
    if vp_filter_ok and not vp_soft_fail:
      score += 6
      tags.append("VP filter pass")

  ha = compute_ha_roc(df)
  if ha.get("status") == "ok":
    if is_long and ha.get("ha_bull") and ha.get("roc_positive"):
      score += 10
      tags.append("HA bull + ROC up")
    elif not is_long and ha.get("ha_bear") and ha.get("roc_negative"):
      score += 10
      tags.append("HA bear + ROC down")

  session = detect_session_liquidity(df)
  if session.get("status") == "ok" and session.get("session") in ("london", "london_ny", "ny"):
    score += 5
    tags.append(session["tag"])

  obi = compute_obi(exchange, symbol) if exchange and symbol else {"available": False}
  if obi.get("available"):
    imb = float(obi.get("imbalance", 0))
    if is_long and obi.get("obi_bullish"):
      score += 8
      tags.append("OBI bid pressure")
    elif not is_long and obi.get("obi_bearish"):
      score += 8
      tags.append("OBI ask pressure")

  # Core entry: Sweep + OB + FVG confluence (Phase 1 priority)
  sweep_hit = bool(recent_sweep)
  confluence = sweep_hit and bool(active_ob) and bool(active_fvg)
  partial_confluence = sum([sweep_hit, bool(active_ob), bool(active_fvg)])
  msb_ok = msb_allows_entry(msb)
  if msb.get("status") == "ok" and msb.get("pass"):
    tags.append("MSB pass blocked (anti-predictive)")

  structure_blocked = structure_blocks_entry(structure_event, dir_norm)
  zone_top, zone_bot = _zone_bounds(active_ob, active_fvg)
  entry_confirm = detect_entry_confirmation(df, dir_norm, zone_top, zone_bot)

  # Full entry: 3/3 + VP + confirm; MSB pass hard-blocked; no counter-trend structure
  pattern_signal = confluence and vp_filter_ok and msb_ok and not structure_blocked
  entry_signal = pattern_signal and entry_confirm["confirmed"]
  entry_probe = (
    not pattern_signal
    and partial_confluence >= 2
    and vp_filter_ok
    and msb_ok
    and score >= 42
    and not structure_blocked
  )

  return {
    "timeframe": tf,
    "status": "ok",
    "score": min(100, score),
    "tags": tags,
    "smc_source": smc.get("source", "unknown"),
    "structure_event": structure_event,
    "active_ob": active_ob,
    "active_fvg": active_fvg,
    "recent_sweep": recent_sweep,
    "eq_sweep": eq_sweep,
    "eq_levels": eq_levels if eq_levels.get("status") == "ok" else None,
    "msb_zscore": msb,
    "cvd_divergence": cvd_div,
    "volume_profile": vp,
    "vp_filter_ok": vp_filter_ok,
    "vp_soft_fail": vp_soft_fail,
    "ha_roc": ha,
    "obi": obi,
    "session": session,
    "confluence": confluence,
    "partial_confluence": partial_confluence,
    "structure_blocked": structure_blocked,
    "entry_confirm_ok": entry_confirm["confirmed"],
    "entry_confirm_mode": entry_confirm["mode"],
    "entry_signal": entry_signal,
    "entry_probe": entry_probe,
    "entry_grade": "A" if entry_signal and score >= 55 else (
      "B" if (entry_probe or (partial_confluence >= 2 and score >= 40)) else (
        "C" if score >= 25 else "D"
      )
    ),
  }


def build_institutional_matrix(
  data: Dict[str, pd.DataFrame],
  direction: str,
  tfs: Optional[List[str]] = None,
  exchange=None,
  symbol: str = "",
) -> dict:
  """Analyze institutional edge across entry timeframes (15m, 1h primary)."""
  tfs = tfs or ["15m", "1h", "4h"]
  by_tf = {}
  for tf in tfs:
    df = data.get(tf)
    if df is None or len(df) < 40:
      by_tf[tf] = {"status": "no_data"}
      continue
    by_tf[tf] = analyze_institutional_tf(df, tf, direction, exchange, symbol)

  entry_tfs = [t for t in ("15m", "1h") if by_tf.get(t, {}).get("status") == "ok"]
  best_entry = max(
    (by_tf[t] for t in entry_tfs),
    key=lambda x: (x.get("entry_signal", False), x.get("entry_probe", False), x.get("score", 0)),
    default=None,
  )
  scores = [by_tf[t]["score"] for t in entry_tfs if by_tf.get(t, {}).get("score")]
  all_tags: List[str] = []
  for t in entry_tfs:
    all_tags.extend(by_tf[t].get("tags", []))

  return {
    "by_tf": by_tf,
    "best_entry_tf": best_entry.get("timeframe") if best_entry else None,
    "entry_signal": bool(best_entry and best_entry.get("entry_signal")),
    "entry_probe": bool(best_entry and best_entry.get("entry_probe")),
    "entry_confirm_ok": bool(best_entry and best_entry.get("entry_confirm_ok")),
    "entry_confirm_mode": best_entry.get("entry_confirm_mode") if best_entry else None,
    "structure_blocked": bool(best_entry and best_entry.get("structure_blocked")),
    "entry_grade": best_entry.get("entry_grade", "D") if best_entry else "D",
    "institutional_score": max(scores) if scores else 0,
    "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
    "tags": list(dict.fromkeys(all_tags)),
    "confluence_count": best_entry.get("partial_confluence", 0) if best_entry else 0,
    "vp_filter_ok": all(by_tf.get(t, {}).get("vp_filter_ok", True) for t in entry_tfs),
  }
