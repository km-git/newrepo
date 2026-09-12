"""Statistical helpers for honest rate reporting."""

from __future__ import annotations

import math
from typing import Optional, Tuple

# Minimum sample for headline win-rate display (tables, board tags)
MIN_HEADLINE_N = 10


def wilson_ci(wins: int, n: int, z: float = 1.96) -> Tuple[Optional[float], Optional[float]]:
  """Wilson score interval for binomial proportion. Returns (low, high) in [0,1]."""
  if n <= 0:
    return None, None
  p = wins / n
  z2 = z * z
  denom = 1 + z2 / n
  center = (p + z2 / (2 * n)) / denom
  margin = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n) / denom
  return max(0.0, center - margin), min(1.0, center + margin)


def rate_display(win_rate: Optional[float], n: int, wins: Optional[int] = None) -> str:
  """Headline rate string with Wilson 95% CI, blank when n < MIN_HEADLINE_N."""
  if n < MIN_HEADLINE_N or win_rate is None:
    return ""
  if wins is None:
    wins = int(round(float(win_rate) * n))
  lo, hi = wilson_ci(wins, n)
  if lo is None or hi is None:
    return f"{float(win_rate):.1%} (n={n})"
  return f"{float(win_rate):.1%} [{lo:.1%}–{hi:.1%}] (n={n})"
