"""V6 multi-timeframe setup — 6 TFs for large-scale continuous scanning."""

from __future__ import annotations

import os
from typing import List, Tuple

# User-facing V6 stack: 15m → 1w (6 timeframes including 12h)
V6_TIMEFRAMES: Tuple[str, ...] = ("1w", "1d", "12h", "4h", "1h", "15m")
V6_TIMEFRAMES_DISPLAY: Tuple[str, ...] = ("15m", "1h", "4h", "12h", "1d", "1w")

DEFAULT_SCANNER_PAIRS = 1000
DEFAULT_SCANNER_CHUNK = 50
DEFAULT_SCANNER_BATCH_INTERVAL = 7200  # 2h between full-universe rotations
DEFAULT_SCANNER_MONITOR_INTERVAL = 300


def v6_enabled() -> bool:
  return os.environ.get("EW_V6_SETUP", "1").lower() not in ("0", "false", "no")


def active_timeframes() -> List[str]:
  """Return V6 (6 TF) or legacy 5-TF list based on EW_V6_SETUP."""
  if v6_enabled():
    return list(V6_TIMEFRAMES)
  return ["1w", "1d", "4h", "1h", "15m"]


def scanner_pair_target() -> int:
  try:
    return max(1, int(os.environ.get("EW_SCANNER_PAIRS", str(DEFAULT_SCANNER_PAIRS))))
  except (TypeError, ValueError):
    return DEFAULT_SCANNER_PAIRS


def scanner_chunk_size() -> int:
  try:
    return max(1, int(os.environ.get("EW_SCANNER_CHUNK", str(DEFAULT_SCANNER_CHUNK))))
  except (TypeError, ValueError):
    return DEFAULT_SCANNER_CHUNK
