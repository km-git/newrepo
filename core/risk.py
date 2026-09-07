"""Dynamic DCA legs, stop-loss, and take-profit targeting."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


# Asymmetric pyramiding: lightest at first touch, heaviest at max confluence/discount.
DCA_SPLITS = [10, 20, 30, 40]
DCA_LABELS = ["L1", "L2", "L3", "L4"]

DCA_PROFILE_PYRAMID = "pyramid_4"
DCA_PROFILE_10_90 = "two_layer_10_90"
DCA_PROFILE_30_70 = "two_layer_30_70"

PROFILE_SPLITS = {
  DCA_PROFILE_PYRAMID: [10, 20, 30, 40],
  DCA_PROFILE_10_90: [10, 90],
  DCA_PROFILE_30_70: [30, 70],
}

DEFAULT_MAX_STRUCTURE_ATR = 4.0
DEFAULT_MAX_STOP_ATR = 5.0

# Min / max stop distance (% of WAE) by timeframe — room to breathe, capped for risk.
TF_STOP_PCT: Dict[str, Tuple[float, float]] = {
  "15m": (0.85, 3.5),
  "1h": (1.15, 4.5),
  "4h": (1.35, 5.5),
  "12h": (1.55, 6.5),
  "1d": (1.75, 8.0),
  "1w": (2.5, 12.0),
}
DEFAULT_STOP_PCT = (1.0, 6.0)

# R-multiples for smart targets (TP1 / TP2 / TP3) by timeframe.
TF_TARGET_R: Dict[str, Tuple[float, float, float]] = {
  "15m": (1.25, 2.25, 3.75),
  "1h": (1.5, 2.75, 4.5),
  "4h": (1.75, 3.0, 5.0),
  "12h": (1.85, 3.25, 5.5),
  "1d": (2.0, 3.5, 6.0),
  "1w": (2.5, 4.5, 8.0),
}
DEFAULT_TARGET_R = (1.5, 2.5, 4.0)

# Golden-ratio scale-in depths inside the entry zone (0 = near-side, 1 = far-side).
_ZONE_DEPTH_RATIOS = [0.0, 0.382, 0.618, 1.0]

_DCA_RATIONALE_LONG = [
  "zone boundary — first touch, minimal exposure (10%)",
  "zone 0.382 — confirmed discount (20%)",
  "zone 0.618 — structural confluence (30%)",
  "zone floor — maximum discount, maximum conviction (40%)",
]
_DCA_RATIONALE_SHORT = [
  "zone boundary — first supply probe (10%)",
  "zone 0.382 — confirmed rejection (20%)",
  "zone 0.618 — deep supply confluence (30%)",
  "zone ceiling — maximum short conviction (40%)",
]


def _r(x: float, decimals: int = 6) -> float:
  ax = abs(float(x))
  if ax > 0 and ax < 1:
    # Preserve at least eight significant decimals for micro-priced tokens.
    # A fixed 10-decimal round turned valid 1e-8 geometry into zeros/negative R:R.
    decimals = max(decimals, min(18, int(-math.floor(math.log10(ax))) + 8))
  return round(float(x), decimals)


def _clamp(x: float, lo: float, hi: float) -> float:
  return max(lo, min(hi, x))


def _eps(reference: float) -> float:
  """Scale-safe positive epsilon (fixed 1e-9 breaks micro-priced tokens)."""
  return max(abs(float(reference)) * 1e-12, 1e-18)


def _is_long(direction: str) -> bool:
  return direction.upper() in ("LONG", "BULL")


def compute_wae(legs: List[dict]) -> float:
  """Weighted average entry: Σ(price × allocation%)."""
  total = sum(float(leg["price"]) * float(leg["size_pct"]) / 100.0 for leg in legs)
  return _r(total)


def sensible_entry_anchor(
  direction: str,
  current: float,
  zone_low: float,
  zone_high: float,
  atr: float,
) -> float:
  """
  First limit away from chasing extended price.
  LONG: pullback into upper zone, strictly below market.
  SHORT: rally into supply — above market when price has already left the zone.
  """
  if current <= 0:
    return current
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  span = hi - lo if hi > lo else 0.0
  buf = max(atr * 0.12, abs(current) * 0.0008, span * 0.04 if span else 0.0, _eps(current))
  long = _is_long(direction)

  if long:
    if hi > 0 and current > hi:
      ideal = hi - buf * 0.35
    else:
      ideal = hi - buf * 0.35 if span > 0 else current - buf
    ideal = min(ideal, current - buf)
    if span > 0:
      ideal = _clamp(ideal, lo + span * 0.08, hi - buf * 0.15)
    return _r(ideal)

  if hi > 0 and current > hi:
    return _r(current + buf)
  ideal = lo + buf * 0.35 if span > 0 else current + buf
  ideal = max(ideal, current + buf)
  if span > 0:
    ideal = _clamp(ideal, lo + buf * 0.15, hi - span * 0.08)
  return _r(ideal)


def clamp_ladder_no_chase(
  current: float,
  direction: str,
  prices: List[float],
  atr: float,
  zone_low: float,
  zone_high: float,
) -> List[float]:
  """Limit legs must not chase: LONG buys below, SHORT sells above current."""
  if current <= 0 or not prices:
    return prices
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  span = hi - lo if hi > lo else 0.0
  buf = max(atr * 0.1, abs(current) * 0.0005, span * 0.06 if span else 0.0, _eps(current))
  long = _is_long(direction)
  out = [_r(p) for p in prices]

  if long:
    if hi > 0 and current > hi:
      # Extended above zone — wait for pullback into zone ceiling, never chase higher.
      cap = current - buf
      out[0] = min(out[0], hi - buf * 0.2, cap)
      out[0] = _clamp(out[0], lo if lo > 0 else out[0], hi)
      for i in range(1, len(out)):
        out[i] = min(out[i], out[i - 1] - buf * 0.25, cap)
      if lo > 0:
        out[-1] = max(out[-1], lo)
    else:
      cap = current - buf
      out[0] = min(out[0], cap)
      if lo > 0 and hi > lo:
        out[0] = _clamp(out[0], lo, hi)
      for i in range(1, len(out)):
        out[i] = min(out[i], out[i - 1] - buf * 0.25, cap)
      if lo > 0:
        out[-1] = max(out[-1], lo)
  else:
    if hi > 0 and current > hi:
      # Price above supply zone — sell the rally above market, not into weakness below.
      floor = current + buf
      out[0] = max(out[0], floor)
      for i in range(1, len(out)):
        out[i] = max(out[i], out[i - 1] + buf * 0.25)
      return out
    floor = current + buf
    out[0] = max(out[0], floor)
    if lo > 0 and hi > lo:
      out[0] = _clamp(out[0], lo, hi)
      if out[0] < floor:
        out[0] = _r(floor)
    for i in range(1, len(out)):
      out[i] = max(out[i], out[i - 1] + buf * 0.25, floor)
    if hi > 0:
      out[-1] = min(out[-1], hi) if current <= hi else out[-1]

  return out


def _min_leg_separation(span: float, atr: float, anchor: float) -> float:
  """Minimum price gap between consecutive DCA legs (capped to fit 4 legs in zone)."""
  raw = max(span * 0.08, atr * 0.05, abs(anchor) * 0.0004, _eps(anchor))
  return min(raw, span / 4.5)


def _spread_legs_from_anchor(
  direction: str,
  anchor: float,
  near: float,
  far: float,
  min_sep: float,
) -> List[float]:
  """
  Place L1 at anchor when inside zone, spread L2–L4 toward far-side.
  Uses forward-only spacing so legs never collapse to the same price.
  """
  lo, hi = min(near, far), max(near, far)
  span = hi - lo
  if span <= 0:
    return [_r(anchor)] * 4

  min_sep = min(min_sep, span / 4.5)
  long = _is_long(direction)
  depths = [0.0, 0.33, 0.66, 1.0]

  if long:
    prices = [hi - d * span for d in depths]
    far_side = lo
  else:
    prices = [lo + d * span for d in depths]
    far_side = hi

  if lo <= anchor <= hi:
    rem = abs(anchor - far_side)
    if rem >= min_sep * 3:
      prices[0] = anchor
      inner = [0.35, 0.65, 1.0]
      if long:
        prices[1:] = [anchor - d * rem for d in inner]
      else:
        prices[1:] = [anchor + d * rem for d in inner]
    # else: keep evenly spaced zone depths — anchor too close to far side to pyramid from it

  if long:
    for i in range(1, len(prices)):
      prices[i] = min(prices[i], prices[i - 1] - min_sep)
    prices[-1] = lo
    if len(prices) > 1:
      prices[-2] = max(prices[-2], lo + min_sep)
      prices[-2] = min(prices[-2], prices[-3] - min_sep) if len(prices) > 2 else prices[-2]
  else:
    for i in range(1, len(prices)):
      prices[i] = max(prices[i], prices[i - 1] + min_sep)
    prices[-1] = hi
    if len(prices) > 1:
      prices[-2] = min(prices[-2], hi - min_sep)
      prices[-2] = max(prices[-2], prices[-3] + min_sep) if len(prices) > 2 else prices[-2]

  return [_r(_clamp(p, lo, hi)) for p in prices]


def _zone_pyramid_prices(
  direction: str,
  anchor: float,
  zone_low: float,
  zone_high: float,
  atr: float,
  harmonic_prz: Optional[Tuple[float, float]] = None,
) -> List[float]:
  """
  Asymmetric pyramid ticks inside the entry zone.
  LONG: L1 highest → L4 lowest. SHORT: L1 lowest → L4 highest.
  Each leg is a distinct price — never collapsed to the same level.
  """
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  span = hi - lo
  if span <= 0:
    span = max(atr * 0.5, abs(anchor) * 0.002, _eps(anchor))
    lo = anchor - span / 2
    hi = anchor + span / 2

  long = _is_long(direction)
  near = hi if long else lo
  far = lo if long else hi
  min_sep = _min_leg_separation(span, atr, anchor)

  if lo <= anchor <= hi:
    # Use anchor only on the conservative (near) side — never chase the far extreme.
    if long:
      l1 = anchor if anchor >= lo + span * 0.45 else near
    else:
      l1 = anchor if anchor <= hi - span * 0.45 else near
  else:
    l1 = near

  prices = _spread_legs_from_anchor(direction, l1, near, far, min_sep)

  if harmonic_prz:
    prz_lo, prz_hi = min(harmonic_prz), max(harmonic_prz)
    prz_lo, prz_hi = _clamp(prz_lo, lo, hi), _clamp(prz_hi, lo, hi)
    if prz_hi - prz_lo >= min_sep:
      if long:
        prices[1] = _clamp(prz_hi - 0.25 * (prz_hi - prz_lo), lo, hi)
        prices[2] = _clamp(prz_lo + 0.25 * (prz_hi - prz_lo), lo, hi)
      else:
        prices[1] = _clamp(prz_lo + 0.25 * (prz_hi - prz_lo), lo, hi)
        prices[2] = _clamp(prz_hi - 0.25 * (prz_hi - prz_lo), lo, hi)
      prices = _spread_legs_from_anchor(direction, prices[0], near, far, min_sep)

  return prices


def build_dca_ladder(
  direction: str,
  anchor: float,
  atr: float,
  zone_low: float,
  zone_high: float,
  fib_levels: Optional[List[float]] = None,
  *,
  harmonic_prz: Optional[Tuple[float, float]] = None,
  gtc: bool = False,
  profile: str = DCA_PROFILE_PYRAMID,
  current: Optional[float] = None,
) -> List[dict]:
  """
  Asymmetric pyramiding DCA.
  Profiles: pyramid_4 (10/20/30/40), two_layer_10_90, two_layer_30_70.
  """
  if atr <= 0:
    atr = max(abs(anchor) * 0.01, _eps(anchor))
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  if lo <= 0 and hi <= 0 and anchor > 0:
    pad = anchor * 0.005
    lo, hi = anchor - pad, anchor + pad

  span = hi - lo
  min_sep = _min_leg_separation(max(span, abs(anchor) * 0.002), atr, anchor)
  if span < min_sep * 3:
    pad = max(min_sep * 2, atr * 0.15, abs(anchor) * 0.002, _eps(anchor))
    if anchor > 0:
      lo, hi = min(lo, anchor - pad), max(hi, anchor + pad)
    else:
      lo, hi = lo - pad, hi + pad

  pyramid_prices = _zone_pyramid_prices(direction, anchor, lo, hi, atr, harmonic_prz)
  if current and current > 0:
    pyramid_prices = clamp_ladder_no_chase(current, direction, pyramid_prices, atr, lo, hi)
  splits = PROFILE_SPLITS.get(profile, DCA_SPLITS)

  if profile == DCA_PROFILE_PYRAMID:
    prices = pyramid_prices
    labels = DCA_LABELS
    rationales = _DCA_RATIONALE_LONG if _is_long(direction) else _DCA_RATIONALE_SHORT
  elif profile == DCA_PROFILE_10_90:
    prices = [pyramid_prices[0], pyramid_prices[-1]]
    labels = ["L1", "L2"]
    rationales = [
      "first touch — minimum probe (10%)",
      "max confluence depth — near-full size (90%)",
    ]
  else:  # 30_70
    prices = [pyramid_prices[0], pyramid_prices[-1]]
    labels = ["L1", "L2"]
    rationales = [
      "hard level — elevated probe (30%)",
      "extended floor — maximum conviction (70%)",
    ]

  legs: List[dict] = []
  for i, (label, pct, px) in enumerate(zip(labels, splits, prices)):
    rationale = rationales[i] if i < len(rationales) else f"layer {label} ({pct}%)"
    legs.append({
      "leg": i + 1,
      "layer": label,
      "size_pct": pct,
      "price": px,
      "rationale": rationale,
      "order_type": "limit" if (gtc or i > 0) else "market",
      "time_in_force": "GTC" if gtc else ("GTC" if i > 0 else "IOC"),
      "trigger": f"GTC limit @ {px}" if (gtc or i > 0) else "immediate",
      "profile": profile,
    })

  wae = compute_wae(legs)
  for leg in legs:
    leg["wae"] = wae
  return legs


def _clamp_structure_to_entry(
  direction: str,
  entry: float,
  atr: float,
  structure_low: float,
  structure_high: float,
  max_atr: float = DEFAULT_MAX_STRUCTURE_ATR,
) -> Tuple[float, float]:
  if atr <= 0:
    atr = max(abs(entry) * 0.01, _eps(entry))
  band = max_atr * atr
  s_low = _clamp(structure_low, entry - band, entry)
  s_high = _clamp(structure_high, entry, entry + band)
  if s_low > s_high:
    s_low, s_high = s_high, s_low
  return s_low, s_high


def _stop_pct_bounds(timeframe: Optional[str]) -> Tuple[float, float]:
  if timeframe and timeframe in TF_STOP_PCT:
    return TF_STOP_PCT[timeframe]
  return DEFAULT_STOP_PCT


def min_stop_distance_pct(timeframe: Optional[str] = None) -> float:
  """Minimum stop distance (% of entry) for a timeframe."""
  return _stop_pct_bounds(timeframe)[0]


def stop_distance_pct(entry: float, stop: float) -> float:
  if entry <= 0 or stop <= 0:
    return 0.0
  return _r(abs(entry - stop) / entry * 100.0, 2)


# Heuristic DCA staging SL tuning (user idea: wide L1 → ~2.3% WAE with 10/20/30/40).
_DCA_SL_WIDE_BASE = 3.0
_DCA_SL_TARGET_BASE = 2.3
_DCA_SL_MIN_REDUCTION_PP = 0.5


def dca_sl_wide_threshold(timeframe: Optional[str] = None) -> float:
  """L1-only stop % above which pyramid staging is worth considering."""
  min_pct, _ = _stop_pct_bounds(timeframe)
  return _r(max(_DCA_SL_WIDE_BASE, min_pct * 2.2), 2)


def dca_sl_target_pct(timeframe: Optional[str] = None) -> float:
  """Target effective stop % after smart DCA fills (TF-scaled from ~2.3% base)."""
  min_pct, max_pct = _stop_pct_bounds(timeframe)
  scaled = max(_DCA_SL_TARGET_BASE, min_pct * 1.65)
  return _r(min(scaled, max_pct * 0.72), 2)


def _partial_wae(legs: List[dict], n_legs: int) -> float:
  sub = legs[:n_legs]
  if not sub:
    return 0.0
  total = sum(float(leg["size_pct"]) for leg in sub)
  if total <= 0:
    return 0.0
  norm = [{"price": leg["price"], "size_pct": float(leg["size_pct"]) / total * 100.0} for leg in sub]
  return compute_wae(norm)


def dca_stop_metrics(
  legs: List[dict],
  stop_price: float,
  *,
  timeframe: Optional[str] = None,
) -> Dict[str, Any]:
  """
  Compare L1-only vs pyramid WAE stop distance.

  Returns TF-aware wide/target thresholds, reduction, min legs to hit target,
  and whether staging resolves a wide L1 into the practical risk band.
  """
  if not legs or stop_price <= 0:
    return {
      "l1_stop_distance_pct": 0.0,
      "stop_distance_pct": 0.0,
      "dca_stop_reduction_pct": 0.0,
      "dca_sl_wide_threshold_pct": dca_sl_wide_threshold(timeframe),
      "dca_sl_target_pct": dca_sl_target_pct(timeframe),
      "dca_staging_legs": 0,
      "dca_sl_resolvable": "N",
      "dca_staging_note": "no_ladder",
    }

  stop_px = float(stop_price)
  l1_px = float(legs[0]["price"])
  wae = compute_wae(legs)
  l1_pct = stop_distance_pct(l1_px, stop_px)
  wae_pct = stop_distance_pct(wae, stop_px)
  reduction = round(max(0.0, l1_pct - wae_pct), 2)
  wide_thr = dca_sl_wide_threshold(timeframe)
  target = dca_sl_target_pct(timeframe)

  staging_legs = len(legs)
  for n in range(1, len(legs) + 1):
    partial = _partial_wae(legs, n)
    if partial > 0 and stop_distance_pct(partial, stop_px) <= target:
      staging_legs = n
      break

  if l1_pct <= target:
    note = "l1_within_target"
  elif l1_pct > wide_thr and wae_pct <= target and reduction >= _DCA_SL_MIN_REDUCTION_PP:
    note = f"pyramid_L{staging_legs}_to_{target:.1f}pct"
  elif l1_pct > wide_thr and reduction >= _DCA_SL_MIN_REDUCTION_PP:
    note = f"pyramid_L{staging_legs}_partial_{wae_pct:.1f}pct"
  elif l1_pct > wide_thr:
    note = "wide_l1_no_pyramid_relief"
  else:
    note = "moderate_l1"

  resolvable = (
    l1_pct > wide_thr
    and wae_pct <= target
    and reduction >= _DCA_SL_MIN_REDUCTION_PP
  )

  return {
    "l1_stop_distance_pct": l1_pct,
    "stop_distance_pct": wae_pct,
    "dca_stop_reduction_pct": reduction,
    "dca_sl_wide_threshold_pct": wide_thr,
    "dca_sl_target_pct": target,
    "dca_staging_legs": staging_legs,
    "dca_sl_resolvable": "Y" if resolvable else "N",
    "dca_staging_note": note,
  }


def _target_r_multiples(timeframe: Optional[str]) -> Tuple[float, float, float]:
  if timeframe and timeframe in TF_TARGET_R:
    return TF_TARGET_R[timeframe]
  return DEFAULT_TARGET_R


def _smart_stop_distance_pct(
  ref: float,
  atr: float,
  zone_low: float,
  zone_high: float,
  timeframe: Optional[str],
) -> Tuple[float, float]:
  """Blend TF floor, zone width, and ATR — never razor-thin."""
  min_pct, max_pct = _stop_pct_bounds(timeframe)
  if ref <= 0:
    return min_pct, max_pct
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  span = hi - lo if hi > lo else 0.0
  zone_pct = span / ref * 100.0 * 1.2 if span > 0 else 0.0
  atr_pct = atr / ref * 100.0 * 1.75 if atr > 0 else 0.0
  effective_min = max(min_pct, zone_pct, atr_pct)
  return min(effective_min, max_pct), max_pct


def _ladder_extreme(direction: str, legs: Optional[List[dict]], entry: float) -> float:
  """Worst-case fill: lowest leg for LONG, highest for SHORT."""
  if not legs:
    return entry
  prices = [float(leg["price"]) for leg in legs if leg.get("price")]
  if not prices:
    return entry
  return min(prices) if _is_long(direction) else max(prices)


def stop_is_sane(
  direction: str,
  entry: float,
  stop: float,
  atr: float,
  *,
  max_atr: float = DEFAULT_MAX_STOP_ATR,
  timeframe: Optional[str] = None,
  zone_low: Optional[float] = None,
  zone_high: Optional[float] = None,
) -> bool:
  if entry <= 0 or stop <= 0 or atr <= 0:
    return False
  if _is_long(direction):
    if stop >= entry:
      return False
  else:
    if stop <= entry:
      return False

  dist_pct = abs(entry - stop) / entry * 100.0
  min_pct, max_pct = _stop_pct_bounds(timeframe)
  if dist_pct < min_pct * 0.85 or dist_pct > max_pct * 1.05:
    return False
  if abs(entry - stop) > max_atr * atr * 1.05:
    return False

  if zone_low is not None and zone_high is not None:
    lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
    if _is_long(direction) and stop > lo:
      return False
    if not _is_long(direction) and stop < hi:
      return False
  return True


def dynamic_stop(
  direction: str,
  entry: float,
  atr: float,
  structure_low: float,
  structure_high: float,
  atr_mult: float = 1.0,
  *,
  zone_low: Optional[float] = None,
  zone_high: Optional[float] = None,
  max_structure_atr: float = DEFAULT_MAX_STRUCTURE_ATR,
  max_stop_atr: float = DEFAULT_MAX_STOP_ATR,
  timeframe: Optional[str] = None,
  ladder_legs: Optional[List[dict]] = None,
) -> dict:
  """
  Smart hard stop: zone invalidation + structure + DCA ladder extreme.

  Distance is the wider of (zone breach, TF/ATR/zone-width floor) — never
  clipped to the minimum by a tight invalidation tick.
  """
  if atr <= 0:
    atr = max(abs(entry) * 0.01, _eps(entry))

  ref = _ladder_extreme(direction, ladder_legs, entry)
  lo = hi = None
  if zone_low is not None and zone_high is not None:
    lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
    if hi - lo <= 0:
      lo, hi = None, None

  if lo is None or hi is None:
    pad = max(atr * 0.65, ref * 0.006)
    lo, hi = ref - pad, ref + pad

  min_pct, max_pct = _smart_stop_distance_pct(ref, atr, lo, hi, timeframe)
  buffer = max(atr_mult * 0.45 * atr, ref * min_pct / 100.0 * 0.25, (hi - lo) * 0.12)

  band = min(max_structure_atr * atr, ref * max_pct / 100.0)
  s_low, s_high = _clamp_structure_to_entry(
    direction, ref, atr, structure_low, structure_high, max_structure_atr,
  )

  if _is_long(direction):
    near_struct = s_low if abs(s_low - lo) <= band else lo
    zone_stop = min(lo, near_struct) - buffer
    pct_stop = ref * (1.0 - min_pct / 100.0)
    wide_cap = ref * (1.0 - max_pct / 100.0)
    stop = min(zone_stop, pct_stop)
    stop = max(stop, wide_cap)
    rule = (
      f"smart SL below zone {_r(lo)} / struct — "
      f"min {min_pct:.2f}% · zone+ATR floor (max {max_pct}%)"
    )
  else:
    near_struct = s_high if abs(s_high - hi) <= band else hi
    zone_stop = max(hi, near_struct) + buffer
    pct_stop = ref * (1.0 + min_pct / 100.0)
    wide_cap = ref * (1.0 + max_pct / 100.0)
    stop = max(zone_stop, pct_stop)
    stop = min(stop, wide_cap)
    rule = (
      f"smart SL above zone {_r(hi)} / struct — "
      f"min {min_pct:.2f}% · zone+ATR floor (max {max_pct}%)"
    )

  atr_cap = max_stop_atr * atr
  if _is_long(direction):
    stop = max(stop, ref - atr_cap)
  else:
    stop = min(stop, ref + atr_cap)

  dist_pct = abs(ref - stop) / ref * 100.0 if ref else 0.0
  if dist_pct < min_pct * 0.9:
    if _is_long(direction):
      stop = ref * (1.0 - min_pct / 100.0)
    else:
      stop = ref * (1.0 + min_pct / 100.0)

  # Final cap: WAE-sized risk must respect TF max (caller passes entry=WAE separately)
  stop = cap_stop_for_entry(direction, entry, stop, timeframe=timeframe)

  return {
    "price": _r(stop),
    "type": "hard",
    "rule": rule,
    "distance_pct": _r(abs(entry - stop) / entry * 100, 2) if entry else 0.0,
    "reference_price": _r(entry),
    "ladder_extreme_price": _r(ref),
    "min_distance_pct": _r(min_pct, 2),
    "architecture": "smart_dynamic_sl",
  }


def dynamic_targets(
  direction: str,
  entry: float,
  atr: float,
  harmonic_prz: Optional[Tuple[float, float]] = None,
  c_target_100: Optional[float] = None,
  c_target_161: Optional[float] = None,
  *,
  stop_price: Optional[float] = None,
  zone_low: Optional[float] = None,
  zone_high: Optional[float] = None,
  timeframe: Optional[str] = None,
  structure_low: Optional[float] = None,
  structure_high: Optional[float] = None,
  max_rr_cap: float = 5.0,
) -> List[dict]:
  """
  Smart R-based targets from actual WAE→stop risk, structure, and harmonics.

  TP1/2/3 use TF R-multiples; anchors lift to zone mid/opposite edge and
  wave structure when those levels improve the reward profile.
  """
  r1, r2, r3 = _target_r_multiples(timeframe)
  risk = abs(entry - stop_price) if stop_price and stop_price > 0 else max(atr * 1.25, entry * 0.01)
  lo = hi = None
  if zone_low is not None and zone_high is not None:
    lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
    if hi <= lo:
      lo, hi = None, None

  long = _is_long(direction)
  if long:
    t1 = entry + risk * r1
    t2 = entry + risk * r2
    t3 = entry + risk * r3
    if lo is not None and hi is not None:
      t1 = max(t1, (lo + hi) / 2.0)
      t1 = max(t1, min(hi, entry + risk * r1 * 1.15))
    if _valid_structure_anchor("LONG", entry, structure_high, atr):
      t2 = max(t2, min(structure_high, entry + risk * max_rr_cap))
    if harmonic_prz:
      prz_hi = float(harmonic_prz[1])
      if prz_hi > entry:
        t2 = max(t2, min(prz_hi, entry + risk * max_rr_cap))
    if _valid_c_target("LONG", entry, c_target_100):
      t3 = max(t3, min(float(c_target_100), entry + risk * max_rr_cap))
    if _valid_c_target("LONG", entry, c_target_161):
      t3 = max(t3, min(float(c_target_161), entry + risk * max_rr_cap))
    # enforce ascending ladder
    t1 = max(t1, entry + risk * 0.5)
    t1 = min(t1, entry + risk * max(0.5, max_rr_cap - 0.5))
    t2 = max(t2, t1 + risk * 0.25)
    t3 = max(t3, t2 + risk * 0.25)
    t2 = min(t2, entry + risk * max_rr_cap)
    t3 = min(t3, entry + risk * (max_rr_cap + 1.5))
  else:
    t1 = entry - risk * r1
    t2 = entry - risk * r2
    t3 = entry - risk * r3
    if lo is not None and hi is not None:
      t1 = min(t1, (lo + hi) / 2.0)
      t1 = min(t1, max(lo, entry - risk * r1 * 1.15))
    if _valid_structure_anchor("SHORT", entry, structure_low, atr):
      t2 = min(t2, max(structure_low, entry - risk * max_rr_cap))
    if harmonic_prz:
      prz_lo = float(harmonic_prz[0])
      if 0 < prz_lo < entry:
        t2 = min(t2, max(prz_lo, entry - risk * max_rr_cap))
    if _valid_c_target("SHORT", entry, c_target_100):
      t3 = min(t3, max(float(c_target_100), entry - risk * max_rr_cap))
    if _valid_c_target("SHORT", entry, c_target_161):
      t3 = min(t3, max(float(c_target_161), entry - risk * max_rr_cap))
    t1 = min(t1, entry - risk * 0.5)
    t1 = max(t1, entry - risk * max(0.5, max_rr_cap - 0.5))
    t2 = min(t2, t1 - risk * 0.25)
    t3 = min(t3, t2 - risk * 0.25)
    t2 = max(t2, entry - risk * max_rr_cap)
    t3 = max(t3, entry - risk * (max_rr_cap + 1.5))

  exits = [50, 25, 25]
  labels = ["TP1", "TP2", "TP3"]
  prices = [t1, t2, t3]
  out = []
  for label, px, pct in zip(labels, prices, exits):
    rr = abs(px - entry) / max(risk, _eps(entry))
    out.append({
      "label": label,
      "price": _r(px),
      "exit_pct": pct,
      "rr": _r(rr, 2),
      "r_multiple": _r(rr, 2),
      "architecture": "smart_dynamic_tp",
    })
  return out


def risk_package(entry: float, stop: float, account_risk_pct: float = 1.0) -> dict:
  risk_per_unit = abs(entry - stop)
  risk_pct = risk_per_unit / entry * 100 if entry else 0
  return {
    "account_risk_pct": account_risk_pct,
    "risk_per_unit_pct": _r(risk_pct, 3),
    "sizing_rule": f"Risk {account_risk_pct}% account; size = (equity×{account_risk_pct}%) / (WAE−stop)",
    "max_legs_active": 4,
  }


def cap_stop_for_entry(
  direction: str,
  entry: float,
  stop: float,
  *,
  timeframe: Optional[str] = None,
) -> float:
  """Tighten stop so WAE→stop distance respects TF max (export sizes on WAE)."""
  if entry <= 0 or stop <= 0:
    return stop
  _, max_pct = _stop_pct_bounds(timeframe)
  dist_pct = abs(entry - stop) / entry * 100.0
  if dist_pct <= max_pct * 1.02:
    return stop
  if _is_long(direction):
    return _r(entry * (1.0 - max_pct / 100.0))
  return _r(entry * (1.0 + max_pct / 100.0))


def _valid_c_target(direction: str, entry: float, value: Optional[float]) -> bool:
  if value is None:
    return False
  try:
    v = float(value)
  except (TypeError, ValueError):
    return False
  if v <= 0:
    return False
  if _is_long(direction):
    return v > entry
  return v < entry


def _valid_structure_anchor(direction: str, entry: float, value: Optional[float], atr: float) -> bool:
  if value is None:
    return False
  try:
    v = float(value)
  except (TypeError, ValueError):
    return False
  if v <= 0:
    return False
  band = max(atr * 12, entry * 0.35, _eps(entry))
  if _is_long(direction):
    return entry < v <= entry + band
  return entry - band <= v < entry


def validate_trade_geometry(
  direction: str,
  entry: float,
  stop: float,
  targets: List[dict],
  *,
  timeframe: Optional[str] = None,
  min_rr: float = 1.2,
  max_rr: float = 5.0,
) -> Tuple[bool, List[str]]:
  """Validate stop + TP ladder relative to WAE entry."""
  errors: List[str] = []
  if entry <= 0:
    errors.append("invalid_entry")
  if stop <= 0:
    errors.append("invalid_stop")
  long = _is_long(direction)
  if entry > 0 and stop > 0:
    if long and stop >= entry:
      errors.append("long_stop_above_entry")
    if not long and stop <= entry:
      errors.append("short_stop_below_entry")

  min_pct, max_pct = _stop_pct_bounds(timeframe)
  sl_pct = stop_distance_pct(entry, stop)
  if sl_pct < min_pct * 0.8:
    errors.append(f"stop_too_tight_{sl_pct:.2f}pct")
  if sl_pct > max_pct * 1.05:
    errors.append(f"stop_too_wide_{sl_pct:.2f}pct")

  tps = [float(t.get("price") or 0) for t in targets[:3]]
  if len(tps) < 3 or any(p <= 0 for p in tps):
    errors.append("invalid_tp_prices")

  if entry > 0 and len(tps) == 3 and all(p > 0 for p in tps):
    if long:
      if not (entry < tps[0] <= tps[1] <= tps[2]):
        errors.append("long_tp_not_ascending")
    else:
      if not (entry > tps[0] >= tps[1] >= tps[2]):
        errors.append("short_tp_not_descending")

  risk = abs(entry - stop) if entry > 0 and stop > 0 else 0.0
  if risk > 0 and len(tps) >= 2 and tps[1] > 0:
    rr2 = abs(tps[1] - entry) / risk
    if rr2 < min_rr * 0.95:
      errors.append(f"rr_below_min_{rr2:.2f}")
    if rr2 > max_rr * 1.05:
      errors.append(f"rr_above_max_{rr2:.2f}")

  return len(errors) == 0, errors
