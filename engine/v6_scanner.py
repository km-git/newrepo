"""V6 scanner — delegates to unified universe_scanner (spot + perps, 6 TFs)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from engine.timeframes import DEFAULT_TFS
from engine.universe_scanner import run_universe_tick
from engine.v6_config import scanner_chunk_size, scanner_pair_target, v6_enabled


def run_v6_chunk_scan(
  *,
  chunk_size: Optional[int] = None,
  output_dir: str = "output",
  quote: str = "USDT",
  include_swap: bool = True,
  force_full: bool = False,
) -> Dict[str, Any]:
  os.environ.setdefault("EW_V6_SETUP", "1")
  os.environ["EW_SCANNER_INCLUDE_SWAP"] = "1" if include_swap else "0"
  if force_full:
    os.environ["UNIVERSE_FORCE_FINALIZE"] = "1"
  result = run_universe_tick(
    universe_size=scanner_pair_target(),
    chunk_size=chunk_size or scanner_chunk_size(),
    tfs=DEFAULT_TFS if v6_enabled() else None,
    output_dir=output_dir,
    quote=quote,
    refresh_pairs=force_full,
  )
  return {
    "ok": True,
    "v6": v6_enabled(),
    "universe_size": result.get("symbols_in_store"),
    "chunk_pairs": result.get("chunk_pairs"),
    "chunk_offset_next": result.get("next_chunk_index"),
    "finalized": result.get("finalized"),
    "best_trades": (result.get("finalize") or {}).get("best_trades_ranked"),
    "finalize": result.get("finalize"),
    "engine": "universe_scanner",
  }


def run_v6_full_batch(
  n: Optional[int] = None,
  output_dir: str = "output",
  quote: str = "USDT",
  include_swap: bool = True,
) -> Dict[str, Any]:
  """Run enough ticks to cover full universe (chunk_size = universe for one-shot)."""
  target = n if n is not None else scanner_pair_target()
  os.environ.setdefault("EW_V6_SETUP", "1")
  os.environ["EW_SCANNER_INCLUDE_SWAP"] = "1" if include_swap else "0"
  result = run_universe_tick(
    universe_size=target,
    chunk_size=target,
    tfs=DEFAULT_TFS if v6_enabled() else None,
    output_dir=output_dir,
    quote=quote,
    refresh_pairs=True,
  )
  return {
    "ok": True,
    "universe_size": target,
    "finalized": result.get("finalized"),
    "best_trades": (result.get("finalize") or {}).get("best_trades_ranked"),
    "finalize": result.get("finalize"),
    "engine": "universe_scanner",
  }


# Backward-compat re-exports
def build_scanner_universe(n: Optional[int] = None, quote: str = "USDT", include_swap: bool = True):
  from fetchers.pairs import fetch_scanner_pairs
  from engine.v6_config import scanner_pair_target

  return fetch_scanner_pairs(
    n=n or scanner_pair_target(),
    quote=quote,
    include_swap=include_swap,
  )
