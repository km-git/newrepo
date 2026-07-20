"""Dynamic DCA legs, stop-loss, and take-profit targeting."""

from __future__ import annotations

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

# Min / max stop distance (% of reference price) by timeframe — common-sense trading bounds.
TF_STOP_PCT: Dict[str, Tuple[float, float]] = {
  "15m": (0.35, 2.5),
  "1h": (0.45, 3.5),
  "4h": (0.55, 4.5),
  "1d": (0.85, 6.5),
  "1w": (1.25, 9.0),
}
DEFAULT_STOP_PCT = (0.5, 5.0)

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
  if ax > 0 and ax < 0.01:
    decimals = 10
  elif ax > 0 and ax < 1:
    decimals = 8
  return round(float(x), decimals)


def _clamp(x: float, lo: float, hi: float) -> float:
  return max(lo, min(hi, x))


def _is_long(direction: str) -> bool:
  return direction.upper() in ("LONG", "BULL")


def compute_wae(legs: List[dict]) -> float:
  """Weighted average entry: Σ(price × allocation%)."""
  total = sum(float(leg["price"]) * float(leg["size_pct"]) / 100.0 for leg in legs)
  return _r(total)


def _min_leg_separation(span: float, atr: float, anchor: float) -> float:
  """Minimum price gap between consecutive DCA legs (capped to fit 4 legs in zone)."""
  raw = max(span * 0.08, atr * 0.05, abs(anchor) * 0.0004, 1e-9)
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
    span = max(atr * 0.5, abs(anchor) * 0.002, 1e-9)
    lo = anchor - span / 2
    hi = anchor + span / 2

  long = _is_long(direction)
  near = hi if long else lo
  far = lo if long else hi
  min_sep = _min_leg_separation(span, atr, anchor)

  if lo <= anchor <= hi:
    l1 = anchor
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
) -> List[dict]:
  """
  Asymmetric pyramiding DCA.
  Profiles: pyramid_4 (10/20/30/40), two_layer_10_90, two_layer_30_70.
  """
  if atr <= 0:
    atr = max(abs(anchor) * 0.01, 1e-9)
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  if lo <= 0 and hi <= 0 and anchor > 0:
    pad = anchor * 0.005
    lo, hi = anchor - pad, anchor + pad

  span = hi - lo
  min_sep = _min_leg_separation(max(span, abs(anchor) * 0.002), atr, anchor)
  if span < min_sep * 3:
    pad = max(min_sep * 2, atr * 0.15, abs(anchor) * 0.002, 1e-9)
    if anchor > 0:
      lo, hi = min(lo, anchor - pad), max(hi, anchor + pad)
    else:
      lo, hi = lo - pad, hi + pad

  pyramid_prices = _zone_pyramid_prices(direction, anchor, lo, hi, atr, harmonic_prz)
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
    atr = max(abs(entry) * 0.01, 1e-9)
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
  Hard stop from zone invalidation + DCA ladder extreme, capped by TF % bounds.

  Stops are placed beyond the entry zone (not arbitrary HTF structure) with
  a minimum buffer so micro-ATR symbols do not get razor-thin stops.
  """
  if atr <= 0:
    atr = max(abs(entry) * 0.01, 1e-9)

  ref = _ladder_extreme(direction, ladder_legs, entry)
  min_pct, max_pct = _stop_pct_bounds(timeframe)
  buffer = max(atr_mult * 0.35 * atr, ref * min_pct / 100.0 * 0.5)

  lo = hi = None
  if zone_low is not None and zone_high is not None:
    lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
    if hi - lo <= 0:
      lo, hi = None, None

  if lo is None or hi is None:
    pad = max(atr * 0.5, ref * 0.005)
    lo, hi = ref - pad, ref + pad

  # Local structure only when it sits near the trade zone (ignore stale HTF noise).
  band = min(max_structure_atr * atr, ref * max_pct / 100.0)
  s_low, s_high = _clamp_structure_to_entry(
    direction, ref, atr, structure_low, structure_high, max_structure_atr,
  )
  if _is_long(direction):
    near_struct = s_low if abs(s_low - lo) <= band else lo
    invalidation = min(lo, near_struct) - buffer
    pct_lo = ref * (1.0 - max_pct / 100.0)
    pct_hi = ref * (1.0 - min_pct / 100.0)
    stop = _clamp(invalidation, pct_lo, pct_hi)
    stop = min(stop, ref - buffer * 0.5)
    rule = f"stop below zone floor {_r(lo)} − buffer (TF {min_pct}-{max_pct}%)"
  else:
    near_struct = s_high if abs(s_high - hi) <= band else hi
    invalidation = max(hi, near_struct) + buffer
    pct_lo = ref * (1.0 + min_pct / 100.0)
    pct_hi = ref * (1.0 + max_pct / 100.0)
    stop = _clamp(invalidation, pct_lo, pct_hi)
    stop = max(stop, ref + buffer * 0.5)
    rule = f"stop above zone ceiling {_r(hi)} + buffer (TF {min_pct}-{max_pct}%)"

  # Final sanity clamp vs ATR cap (secondary to % cap).
  atr_cap = max_stop_atr * atr
  if _is_long(direction):
    stop = max(stop, ref - atr_cap)
  else:
    stop = min(stop, ref + atr_cap)

  return {
    "price": _r(stop),
    "type": "hard",
    "rule": rule,
    "distance_pct": _r(abs(ref - stop) / ref * 100, 2),
    "reference_price": _r(ref),
  }


def dynamic_targets(
  direction: str,
  entry: float,
  atr: float,
  harmonic_prz: Optional[Tuple[float, float]] = None,
  c_target_100: Optional[float] = None,
  c_target_161: Optional[float] = None,
) -> List[dict]:
  """Three-tier targets from WAE with 40/30/30 exit split."""
  if _is_long(direction):
    t1 = entry + atr * 1.5
    t2 = entry + atr * 3.0
    t3 = c_target_100 if c_target_100 and c_target_100 > entry else entry + atr * 5.0
    if harmonic_prz:
      t2 = max(t2, harmonic_prz[1])
    if c_target_161 and c_target_161 > entry:
      t3 = max(t3, c_target_161)
  else:
    t1 = entry - atr * 1.5
    t2 = entry - atr * 3.0
    t3 = c_target_100 if c_target_100 and c_target_100 < entry else entry - atr * 5.0
    if harmonic_prz:
      t2 = min(t2, harmonic_prz[0])
    if c_target_161 and c_target_161 < entry:
      t3 = min(t3, c_target_161)

  exits = [40, 30, 30]
  labels = ["TP1", "TP2", "TP3"]
  prices = [t1, t2, t3]
  out = []
  for label, px, pct in zip(labels, prices, exits):
    rr = abs(px - entry) / max(abs(entry - (entry - atr)), 1e-9)
    out.append({"label": label, "price": _r(px), "exit_pct": pct, "rr": _r(rr, 2)})
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
