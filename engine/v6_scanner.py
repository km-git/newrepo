"""V6 large-scale continuous scanner — chunked batch + best-trade ranking."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.best_trades import export_best_trades
from engine.v6_config import (
  active_timeframes,
  scanner_chunk_size,
  scanner_pair_target,
  v6_enabled,
)
from fetchers.pairs import fetch_scanner_pairs, write_pairs_csv

STATE_PATH = Path("output/v6_scanner/scanner_state.json")


def _load_state() -> dict:
  if not STATE_PATH.exists():
    return {}
  try:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def _save_state(state: dict) -> None:
  STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def build_scanner_universe(
  n: Optional[int] = None,
  quote: str = "USDT",
  include_swap: bool = True,
) -> List[str]:
  target = n if n is not None else scanner_pair_target()
  return fetch_scanner_pairs(n=target, quote=quote, include_swap=include_swap)


def next_chunk_pairs(
  universe: List[str],
  state: dict,
  chunk_size: Optional[int] = None,
) -> tuple[List[str], int]:
  """Rotate through universe; return (chunk, next_offset)."""
  chunk = chunk_size or scanner_chunk_size()
  offset = int(state.get("chunk_offset", 0))
  if offset >= len(universe):
    offset = 0
  end = min(offset + chunk, len(universe))
  pairs = universe[offset:end]
  next_offset = end if end < len(universe) else 0
  return pairs, next_offset


def run_v6_chunk_scan(
  *,
  chunk_size: Optional[int] = None,
  output_dir: str = "output",
  quote: str = "USDT",
  include_swap: bool = True,
  force_full: bool = False,
) -> Dict[str, Any]:
  """
  One scanner cycle:
  - Build universe (up to EW_SCANNER_PAIRS, spot + optional swap)
  - Scan next chunk across V6 timeframes
  - Export limit orders + rank best trades
  """
  state = _load_state()
  tfs = active_timeframes()
  target = scanner_pair_target()
  chunk = chunk_size or scanner_chunk_size()

  if force_full or state.get("universe_size") != target:
    universe = build_scanner_universe(n=target, quote=quote, include_swap=include_swap)
    state["universe"] = universe
    state["universe_size"] = len(universe)
    state["chunk_offset"] = 0
  else:
    universe = state.get("universe") or build_scanner_universe(n=target, quote=quote, include_swap=include_swap)

  if force_full and len(universe) <= chunk:
    pairs = universe
    next_offset = 0
  else:
    pairs, next_offset = next_chunk_pairs(universe, state, chunk_size=chunk)

  ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  out = Path(output_dir)
  out.mkdir(parents=True, exist_ok=True)
  pairs_csv = out / "v6_scanner" / f"chunk_{ts}.csv"
  pairs_csv.parent.mkdir(parents=True, exist_ok=True)
  write_pairs_csv(pairs, str(pairs_csv))

  from engine.batch import run_batch, save_batch_json
  from engine.limit_orders_export import export_limit_orders

  print(f"[v6] scanning {len(pairs)} pairs × {len(tfs)} TFs (V6={v6_enabled()}) offset→{next_offset}/{len(universe)}")
  results = run_batch(str(pairs_csv), tfs, is_crypto=True)
  json_path = out / "v6_scanner" / f"chunk_analysis_{ts}.json"
  save_batch_json(results, str(json_path))

  limit_meta = export_limit_orders(results, output_dir=out)
  best = export_best_trades(
    limit_meta.get("latest_csv", str(out / "latest_limit_orders_all_tf.csv")),
    output_dir=out / "v6_scanner",
    top_n=int(os.environ.get("EW_BEST_TRADES_N", "100")),
  )

  state["chunk_offset"] = next_offset
  state["last_scan_utc"] = datetime.now(timezone.utc).isoformat()
  state["last_chunk"] = {
    "pairs": len(pairs),
    "timeframes": tfs,
    "json": str(json_path),
    "best_trades": best.get("top_10"),
    "executable_count": best.get("executable_scanned"),
  }
  if next_offset == 0 and state.get("chunk_offset") == 0 and len(pairs) == len(universe):
    state["last_full_scan_utc"] = state["last_scan_utc"]
  _save_state(state)

  return {
    "ok": True,
    "v6": v6_enabled(),
    "universe_size": len(universe),
    "chunk_pairs": len(pairs),
    "chunk_offset_next": next_offset,
    "timeframes": tfs,
    "analysis_json": str(json_path),
    "limit_orders_csv": limit_meta.get("latest_csv"),
    "best_trades": best,
    "state_path": str(STATE_PATH),
  }


def run_v6_full_batch(
  n: Optional[int] = None,
  output_dir: str = "output",
  quote: str = "USDT",
  include_swap: bool = True,
) -> Dict[str, Any]:
  """Full universe batch with V6 timeframes."""
  target = n if n is not None else scanner_pair_target()
  pairs = build_scanner_universe(n=target, quote=quote, include_swap=include_swap)
  tfs = active_timeframes()
  out = Path(output_dir)
  ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  pairs_csv = out / "v6_scanner" / f"full_{ts}.csv"
  pairs_csv.parent.mkdir(parents=True, exist_ok=True)
  write_pairs_csv(pairs, str(pairs_csv))

  from engine.batch import run_batch, save_batch_json
  from engine.limit_orders_export import export_limit_orders

  print(f"[v6] FULL scan {len(pairs)} pairs × {len(tfs)} TFs")
  results = run_batch(str(pairs_csv), tfs, is_crypto=True)
  json_path = out / "v6_scanner" / f"full_analysis_{ts}.json"
  save_batch_json(results, str(json_path))
  limit_meta = export_limit_orders(results, output_dir=out)
  best = export_best_trades(
    limit_meta.get("latest_csv", str(out / "latest_limit_orders_all_tf.csv")),
    output_dir=out / "v6_scanner",
  )
  state = _load_state()
  state["universe"] = pairs
  state["universe_size"] = len(pairs)
  state["chunk_offset"] = 0
  state["last_full_scan_utc"] = datetime.now(timezone.utc).isoformat()
  state["last_full_batch"] = {"pairs": len(pairs), "json": str(json_path), "best_top10": best.get("top_10")}
  _save_state(state)
  return {"analysis_json": str(json_path), "limit_orders_csv": limit_meta.get("latest_csv"), "best_trades": best, "universe_size": len(pairs)}
