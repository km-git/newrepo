"""Dynamic DCA legs, stop-loss, and take-profit targeting."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


DCA_SPLITS = [10, 20, 30, 40]

# Max stop distance (% of entry) — stops beyond this are structurally broken
MAX_STOP_PCT = {"scalp": 2.5, "day_trade": 4.0, "swing": 8.0, "long_term": 12.0}


def _r(x: float, decimals: int = 6) -> float:
  return round(float(x), decimals)


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
  mid = (zone_low + zone_high) / 2
  fibs = sorted(fib_levels or [], reverse=(direction == "SHORT"))

  if direction in ("LONG", "BULL"):
    prices = [
      anchor,
      min(anchor - 0.35 * atr, mid),
      min(anchor - 0.75 * atr, zone_low),
      zone_low,
    ]
  else:
    prices = [
      anchor,
      max(anchor + 0.35 * atr, mid),
      max(anchor + 0.75 * atr, zone_high),
      zone_high,
    ]

  if fibs:
    for i, fb in enumerate(fibs[:2]):
      if i + 1 < len(prices):
        prices[i + 1] = fb

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


def cap_stop_price(
  direction: str,
  entry: float,
  stop: float,
  max_pct: float,
) -> tuple[float, bool]:
  """Clamp stop to max % distance from entry. Returns (stop, was_capped)."""
  if not entry or max_pct <= 0:
    return stop, False
  dist_pct = abs(entry - stop) / entry * 100
  if dist_pct <= max_pct:
    return stop, False
  risk = entry * max_pct / 100
  capped = entry - risk if direction in ("LONG", "BULL") else entry + risk
  return _r(capped), True


def dynamic_stop(
  direction: str,
  entry: float,
  atr: float,
  structure_low: float,
  structure_high: float,
  atr_mult: float = 1.0,
  max_stop_pct: Optional[float] = None,
) -> dict:
  if direction in ("LONG", "BULL"):
    base = min(structure_low, entry - 0.5 * atr)
    stop = base - atr_mult * atr
    rule = f"below structure low {_r(structure_low)} − {atr_mult}×ATR"
  else:
    base = max(structure_high, entry + 0.5 * atr)
    stop = base + atr_mult * atr
    rule = f"above structure high {_r(structure_high)} + {atr_mult}×ATR"

  capped_note = ""
  if max_stop_pct is not None:
    stop, was_capped = cap_stop_price(direction, entry, stop, max_stop_pct)
    if was_capped:
      capped_note = f" · capped at {max_stop_pct}% max"
      rule += capped_note

  return {
    "price": _r(stop),
    "type": "dynamic",
    "rule": rule,
    "distance_pct": _r(abs(entry - stop) / entry * 100, 2),
    "capped": bool(capped_note),
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
