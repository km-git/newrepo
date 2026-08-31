"""Batch and parallel OHLC prefetch for outcome resolution and paper simulation."""

from __future__ import annotations

import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_TF_ORDER = ("1w", "1d", "12h", "4h", "1h", "15m")


def _tf_sort_key(tf: str) -> int:
  try:
    return _TF_ORDER.index(tf)
  except ValueError:
    return len(_TF_ORDER)


def parallel_enabled() -> bool:
  return os.environ.get("EW_OHLC_PARALLEL", "1").lower() in ("1", "true", "yes")


def max_workers() -> int:
  return max(1, int(os.environ.get("EW_OHLC_PARALLEL_WORKERS", "8")))


def group_pairs_by_symbol(pairs: Iterable[Tuple[str, str]]) -> Dict[str, List[str]]:
  """Group (symbol, timeframe) pairs into {symbol: [timeframes]}."""
  grouped: Dict[str, set[str]] = defaultdict(set)
  for sym, tf in pairs:
    if sym and tf:
      grouped[sym].add(tf)
  return {sym: sorted(tfs, key=_tf_sort_key) for sym, tfs in grouped.items()}


def prefetch_ohlc(
  pairs: Sequence[Tuple[str, str]],
  *,
  is_crypto: bool = True,
  fetch_fn: Optional[Any] = None,
) -> Dict[str, Any]:
  """
  Prefetch OHLC for unique symbol/timeframe pairs.

  Batches all timeframes per symbol into one fetch call and optionally
  fetches symbols in parallel (EW_OHLC_PARALLEL=1, EW_OHLC_PARALLEL_WORKERS=8).
  Returns cache keyed by ``symbol|timeframe`` -> DataFrame or None.
  """
  if not pairs:
    return {}

  if fetch_fn is None:
    from fetchers import fetch as fetch_fn

  grouped = group_pairs_by_symbol(pairs)
  cache: Dict[str, Any] = {}

  def _fetch_symbol(sym: str, tfs: List[str]) -> Dict[str, Any]:
    local: Dict[str, Any] = {}
    try:
      data = fetch_fn(sym, list(tfs), is_crypto=is_crypto)
      for tf in tfs:
        local[f"{sym}|{tf}"] = data.get(tf)
    except Exception:
      for tf in tfs:
        local[f"{sym}|{tf}"] = None
    return local

  if parallel_enabled() and len(grouped) > 1:
    workers = min(max_workers(), len(grouped))
    with ThreadPoolExecutor(max_workers=workers) as executor:
      futures = {
        executor.submit(_fetch_symbol, sym, tfs): sym
        for sym, tfs in grouped.items()
      }
      for future in as_completed(futures):
        cache.update(future.result())
  else:
    for sym, tfs in grouped.items():
      cache.update(_fetch_symbol(sym, tfs))

  return cache


def prefetch_stats(pairs: Sequence[Tuple[str, str]]) -> Dict[str, int]:
  """Return counts for logging: unique pairs, symbols, and batched fetch calls."""
  grouped = group_pairs_by_symbol(pairs)
  return {
    "unique_pairs": len({f"{s}|{t}" for s, t in pairs}),
    "symbols": len(grouped),
    "fetch_calls": len(grouped),
  }
