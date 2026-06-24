"""Dynamic DCA legs, stop-loss, and take-profit targeting."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


DCA_SPLITS = [10, 20, 30, 40]

# Max distance from entry for structure reference and final stop (in ATR units).
DEFAULT_MAX_STRUCTURE_ATR = 4.0
DEFAULT_MAX_STOP_ATR = 5.0
DCA_LEG_ATR = [0.0, 0.5, 1.0, 1.5]  # per-leg max scale-in distance from anchor


def _r(x: float, decimals: int = 6) -> float:
  return round(float(x), decimals)


def _clamp(x: float, lo: float, hi: float) -> float:
  return max(lo, min(hi, x))


def _scale_in_fibs(
  direction: str,
  anchor: float,
  zone_low: float,
  zone_high: float,
  fib_levels: Optional[List[float]] = None,
) -> List[float]:
  """Fib prices on the scale-in side of anchor, nearest first."""
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  candidates = [float(f) for f in (fib_levels or []) if f is not None]
  if not candidates and lo < hi:
    candidates = [lo, hi]
  # Only use levels inside the entry zone (never HTF cluster prices far from anchor).
  candidates = [f for f in candidates if lo <= f <= hi]
  if direction in ("LONG", "BULL"):
    return sorted([f for f in candidates if f <= anchor], reverse=True)[:2]
  return sorted([f for f in candidates if f >= anchor])[:2]


def _clamp_structure_to_entry(
  direction: str,
  entry: float,
  atr: float,
  structure_low: float,
  structure_high: float,
  max_atr: float = DEFAULT_MAX_STRUCTURE_ATR,
) -> Tuple[float, float]:
  """Keep structure bounds local to entry — ignore stale HTF extremes."""
  if atr <= 0:
    atr = max(abs(entry) * 0.01, 1e-9)
  band = max_atr * atr
  s_low = _clamp(structure_low, entry - band, entry)
  s_high = _clamp(structure_high, entry, entry + band)
  if s_low > s_high:
    s_low, s_high = s_high, s_low
  return s_low, s_high


def build_dca_ladder(
  direction: str,
  anchor: float,
  atr: float,
  zone_low: float,
  zone_high: float,
  fib_levels: Optional[List[float]] = None,
) -> List[dict]:
  """
  Dynamic DCA: 10% / 20% / 30% / 40% across price levels.
  LONG: scale in lower; SHORT: scale in higher.
  """
  if atr <= 0:
    atr = max(abs(anchor) * 0.01, 1e-9)
  lo, hi = min(zone_low, zone_high), max(zone_low, zone_high)
  mid = (lo + hi) / 2
  fibs = _scale_in_fibs(direction, anchor, lo, hi, fib_levels)

  if direction in ("LONG", "BULL"):
    prices = [
      anchor,
      min(anchor - 0.35 * atr, mid),
      min(anchor - 0.75 * atr, lo),
      lo,
    ]
  else:
    prices = [
      anchor,
      max(anchor + 0.35 * atr, mid),
      max(anchor + 0.75 * atr, hi),
      hi,
    ]

  for i, fb in enumerate(fibs[:2]):
    idx = i + 1
    if idx < len(prices):
      prices[idx] = fb

  # Monotonic scale-in + per-leg ATR cap from anchor.
  for i in range(1, len(prices)):
    leg_cap = DCA_LEG_ATR[i] * atr if i < len(DCA_LEG_ATR) else DCA_LEG_ATR[-1] * atr
    if direction in ("LONG", "BULL"):
      cap = anchor - leg_cap
      prices[i] = min(prices[i], prices[i - 1])
      prices[i] = max(prices[i], cap)
    else:
      cap = anchor + leg_cap
      prices[i] = max(prices[i], prices[i - 1])
      prices[i] = min(prices[i], cap)

  legs = []
  for i, (pct, px) in enumerate(zip(DCA_SPLITS, prices)):
    legs.append({
      "leg": i + 1,
      "size_pct": pct,
      "price": _r(px),
      "order_type": "market" if i == 0 else "limit",
      "trigger": "immediate" if i == 0 else f"limit @ {_r(px)}",
    })
  return legs


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
  if direction in ("LONG", "BULL"):
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
  if atr <= 0:
    atr = max(abs(entry) * 0.01, 1e-9)

  s_low, s_high = _clamp_structure_to_entry(
    direction, entry, atr, structure_low, structure_high, max_structure_atr,
  )

  if direction in ("LONG", "BULL"):
    base = min(s_low, entry - 0.5 * atr)
    stop = base - atr_mult * atr
    rule = f"below structure low {_r(s_low)} − {atr_mult}×ATR"
    min_stop = entry - max_stop_atr * atr
    max_stop = entry - 0.25 * atr
    stop = _clamp(stop, min_stop, max_stop)
    if zone_low is not None and zone_high is not None:
      lo = min(zone_low, zone_high)
      zone_stop = lo - atr_mult * atr
      stop = max(stop, zone_stop)
      stop = _clamp(stop, min_stop, max_stop)
      rule = f"max(zone SL @ {_r(zone_stop)}, structure) — capped {max_stop_atr}×ATR"
  else:
    base = max(s_high, entry + 0.5 * atr)
    stop = base + atr_mult * atr
    rule = f"above structure high {_r(s_high)} + {atr_mult}×ATR"
    max_stop = entry + max_stop_atr * atr
    min_stop = entry + 0.25 * atr
    stop = _clamp(stop, min_stop, max_stop)
    if zone_low is not None and zone_high is not None:
      hi = max(zone_low, zone_high)
      zone_stop = hi + atr_mult * atr
      stop = min(stop, zone_stop)
      stop = _clamp(stop, min_stop, max_stop)
      rule = f"min(zone SL @ {_r(zone_stop)}, structure) — capped {max_stop_atr}×ATR"

  return {
    "price": _r(stop),
    "type": "dynamic",
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
  """Three-tier targets with 40/30/30 exit split."""
  if direction in ("LONG", "BULL"):
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
    "sizing_rule": f"Risk {account_risk_pct}% account; size = (equity×{account_risk_pct}%) / (entry−stop)",
    "max_legs_active": 4,
  }
