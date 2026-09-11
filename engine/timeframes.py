"""Shared timeframe constants for batch, board, and universe scanning."""

from __future__ import annotations

# Full universe scan order (intraday → macro)
UNIVERSE_TFS = ["15m", "1h", "4h", "12h", "1d", "1w"]

# Default batch order (macro-first for HTF bias before LTF entries)
DEFAULT_TFS = ["1w", "1d", "12h", "4h", "1h", "15m"]

# Executive board surfaces every TF including context-only mid frames
BOARD_TIMEFRAMES = ("15m", "1h", "4h", "12h", "1d", "1w")

# Context TFs without native style setups — anchor entries from nearest styles
CONTEXT_TIMEFRAMES = {
  "4h": ("day_trade", "swing"),
  "12h": ("swing", "long_term"),
}
