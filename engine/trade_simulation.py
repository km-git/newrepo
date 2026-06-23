"""Shared trade simulation primitives for paper trading and backtest validation."""

from __future__ import annotations

from typing import List, Tuple

MAX_FORWARD_BARS = {"scalp": 48, "day_trade": 72, "swing": 30, "long_term": 12, "smc": 48}
TIER_SIZE = {"full": 1.0, "probe": 0.35, "none": 0.0}
# Reduced-size paper cohort for live-forward SMC validation
SMC_COHORT_SIZE = {"full": 0.50, "probe": 0.25}


def scale_geometry(
  anchor: float,
  stop: float,
  targets: List[dict],
  entry: float,
  direction: str,
) -> Tuple[float, List[dict]]:
  """Preserve stop distance and target R-multiples when entry shifts."""
  risk = abs(anchor - stop)
  if risk <= 0:
    risk = anchor * 0.01
  long = direction == "LONG"
  new_stop = entry - risk if long else entry + risk
  scaled: List[dict] = []
  for t in targets:
    reward = abs(float(t["price"]) - anchor)
    rr = float(t.get("rr", reward / risk if risk else 0))
    px = entry + reward if long else entry - reward
    scaled.append({
      "label": t.get("label", "TP"),
      "price": round(px, 6),
      "exit_pct": t.get("exit_pct", 33),
      "rr": round(rr, 2),
    })
  return new_stop, scaled


def simulate_forward(
  highs: List[float],
  lows: List[float],
  entry: float,
  stop: float,
  targets: List[dict],
  direction: str,
  max_bars: int,
) -> dict:
  """
  Walk forward bars with partial TP exits.
  Conservative: stop checked before targets each bar.
  """
  if not highs or max_bars <= 0:
    return {"outcome": "open", "pnl_r": 0.0, "bars_held": 0, "exit_detail": "no_bars"}

  risk = abs(entry - stop)
  if risk <= 0:
    return {"outcome": "open", "pnl_r": 0.0, "bars_held": 0, "exit_detail": "zero_risk"}

  remaining = 1.0
  pnl_r = 0.0
  long = direction == "LONG"
  tps = sorted(
    [(float(t["price"]), float(t.get("exit_pct", 33)) / 100.0, t.get("label", "TP")) for t in targets],
    key=lambda x: x[0],
    reverse=not long,
  )
  hit_labels: List[str] = []

  for i, (h, l) in enumerate(zip(highs[:max_bars], lows[:max_bars])):
    stopped = (l <= stop) if long else (h >= stop)
    if stopped and remaining > 0:
      pnl_r -= remaining
      return {
        "outcome": "loss",
        "pnl_r": round(pnl_r, 3),
        "bars_held": i + 1,
        "exit_detail": f"stop@{i + 1}",
        "tp_hits": hit_labels,
      }

    for tp_px, exit_frac, label in tps:
      if remaining <= 0:
        break
      hit = (h >= tp_px) if long else (l <= tp_px)
      if hit:
        frac = min(remaining, exit_frac)
        rr = abs(tp_px - entry) / risk
        pnl_r += frac * rr
        remaining -= frac
        hit_labels.append(label)

    if remaining <= 0.01:
      return {
        "outcome": "win",
        "pnl_r": round(pnl_r, 3),
        "bars_held": i + 1,
        "exit_detail": "all_tps",
        "tp_hits": hit_labels,
      }

  if remaining > 0:
    last = highs[min(len(highs), max_bars) - 1]
    unrealized = ((last - entry) / risk) if long else ((entry - last) / risk)
    pnl_r += remaining * unrealized
  return {
    "outcome": "open",
    "pnl_r": round(pnl_r, 3),
    "bars_held": min(len(highs), max_bars),
    "exit_detail": "timeout",
    "tp_hits": hit_labels,
  }


def in_zone(bar_high: float, bar_low: float, bar_close: float, zone: List[float], near_pct: float) -> bool:
  if not zone or len(zone) < 2:
    return True
  zlo, zhi = min(zone), max(zone)
  if bar_low <= zhi and bar_high >= zlo:
    return True
  mid = (zlo + zhi) / 2
  dist = abs(bar_close - mid) / mid * 100 if mid else 99.0
  return dist <= near_pct
