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
  return round(float(x), decimals)


def _clamp(x: float, lo: float, hi: float) -> float:
  return max(lo, min(hi, x))


def _is_long(direction: str) -> bool:
  return direction.upper() in ("LONG", "BULL")


def compute_wae(legs: List[dict]) -> float:
  """Weighted average entry: Σ(price × allocation%)."""
  total = sum(float(leg["price"]) * float(leg["size_pct"]) / 100.0 for leg in legs)
  return _r(total)


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
  """
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  span = hi - lo
  if span <= 0:
    span = max(atr * 0.5, abs(anchor) * 0.002, 1e-9)

  long = _is_long(direction)
  if long:
    # Depth 0 = zone high (near side), depth 1 = zone low (max discount).
    prices = [hi - d * span for d in _ZONE_DEPTH_RATIOS]
    if lo <= anchor <= hi:
      prices[0] = anchor  # first probe at anchor when inside zone
    if harmonic_prz:
      prz_lo, prz_hi = min(harmonic_prz), max(harmonic_prz)
      prz_lo, prz_hi = _clamp(prz_lo, lo, hi), _clamp(prz_hi, lo, hi)
      if prz_hi > prz_lo:
        prices[1] = prz_hi - 0.25 * (prz_hi - prz_lo)
        prices[2] = prz_lo + 0.25 * (prz_hi - prz_lo)
    # Enforce strict descent: L1 ≥ L2 ≥ L3 ≥ L4.
    for i in range(1, len(prices)):
      prices[i] = min(prices[i], prices[i - 1])
    prices[-1] = lo
  else:
    prices = [lo + d * span for d in _ZONE_DEPTH_RATIOS]
    if lo <= anchor <= hi:
      prices[0] = anchor
    if harmonic_prz:
      prz_lo, prz_hi = min(harmonic_prz), max(harmonic_prz)
      prz_lo, prz_hi = _clamp(prz_lo, lo, hi), _clamp(prz_hi, lo, hi)
      if prz_hi > prz_lo:
        prices[1] = prz_lo + 0.25 * (prz_hi - prz_lo)
        prices[2] = prz_hi - 0.25 * (prz_hi - prz_lo)
    for i in range(1, len(prices)):
      prices[i] = max(prices[i], prices[i - 1])
    prices[-1] = hi

  return [_r(p) for p in prices]


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


def stop_is_sane(
  direction: str,
  entry: float,
  stop: float,
  atr: float,
  *,
  max_atr: float = DEFAULT_MAX_STOP_ATR,
) -> bool:
  if entry <= 0 or atr <= 0:
    return False
  if _is_long(direction):
    if stop >= entry:
      return False
  else:
    if stop <= entry:
      return False
  return abs(entry - stop) <= max_atr * atr


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
) -> dict:
  """Hard stop from WAE/entry, structure, and zone invalidation."""
  if atr <= 0:
    atr = max(abs(entry) * 0.01, 1e-9)

  s_low, s_high = _clamp_structure_to_entry(
    direction, entry, atr, structure_low, structure_high, max_structure_atr,
  )

  if _is_long(direction):
    base = min(s_low, entry - 0.5 * atr)
    stop = base - atr_mult * atr
    rule = f"hard stop below structure {_r(s_low)} − {atr_mult}×ATR"
    min_stop = entry - max_stop_atr * atr
    max_stop = entry - 0.25 * atr
    stop = _clamp(stop, min_stop, max_stop)
    if zone_low is not None and zone_high is not None:
      lo = min(zone_low, zone_high)
      zone_stop = lo - atr_mult * atr
      stop = max(stop, zone_stop)
      stop = _clamp(stop, min_stop, max_stop)
      rule = f"hard stop max(zone @ {_r(zone_stop)}, structure) — capped {max_stop_atr}×ATR"
  else:
    base = max(s_high, entry + 0.5 * atr)
    stop = base + atr_mult * atr
    rule = f"hard stop above structure {_r(s_high)} + {atr_mult}×ATR"
    max_stop = entry + max_stop_atr * atr
    min_stop = entry + 0.25 * atr
    stop = _clamp(stop, min_stop, max_stop)
    if zone_low is not None and zone_high is not None:
      hi = max(zone_low, zone_high)
      zone_stop = hi + atr_mult * atr
      stop = min(stop, zone_stop)
      stop = _clamp(stop, min_stop, max_stop)
      rule = f"hard stop min(zone @ {_r(zone_stop)}, structure) — capped {max_stop_atr}×ATR"

  return {
    "price": _r(stop),
    "type": "hard",
    "rule": rule,
    "distance_pct": _r(abs(entry - stop) / entry * 100, 2),
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
