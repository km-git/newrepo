"""Chunked universe scanner — rotate through 1000+ pairs × all timeframes 24/7."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.autodream import build_monitor_queue, save_monitor_queue
from engine.batch import run_batch, save_batch_json
from engine.executive_board import (
  apply_board_to_results,
  build_executive_board,
  save_executive_board,
)
from engine.limit_orders_export import export_limit_orders
from engine.timeframes import UNIVERSE_TFS
from engine.top50_batch import save_batch_summary_csv
from fetchers.pairs import fetch_scanner_pairs, fetch_top_pairs, write_pairs_csv

STATE_PATH = Path(os.environ.get("UNIVERSE_STATE_PATH", "output/autodream/universe_state.json"))
RESULTS_PATH = Path(os.environ.get("UNIVERSE_RESULTS_PATH", "output/autodream/universe_results.json"))
BEST_TRADES_CSV = Path(os.environ.get("UNIVERSE_BEST_TRADES", "output/latest_universe_best_trades.csv"))
PAIRS_CACHE = Path("output/autodream/universe_pairs.json")


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def load_state(path: Optional[Path] = None) -> dict:
  path = path or STATE_PATH
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return {}


def save_state(state: dict, path: Optional[Path] = None) -> None:
  path = path or STATE_PATH
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(state, indent=2, default=str))


def load_results(path: Path = RESULTS_PATH) -> Dict[str, dict]:
  if not path.exists():
    return {}
  try:
    data = json.loads(path.read_text())
    if isinstance(data, list):
      return {r["symbol"]: r for r in data if r.get("symbol")}
    return data if isinstance(data, dict) else {}
  except (json.JSONDecodeError, OSError):
    return {}


def save_results(by_symbol: Dict[str, dict], path: Path = RESULTS_PATH) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(list(by_symbol.values()), indent=2, default=str))


def merge_results(existing: Dict[str, dict], new_rows: List[dict]) -> Dict[str, dict]:
  merged = dict(existing)
  for row in new_rows:
    sym = row.get("symbol")
    if sym:
      merged[sym] = row
  return merged


def refresh_universe_pairs(
  n: int = 1000,
  quote: str = "USDT",
  force: bool = False,
) -> List[str]:
  """Fetch top-N pairs; cache for 6h unless forced."""
  PAIRS_CACHE.parent.mkdir(parents=True, exist_ok=True)
  if PAIRS_CACHE.exists() and not force:
    try:
      doc = json.loads(PAIRS_CACHE.read_text())
      if doc.get("count") == n and doc.get("quote") == quote:
        age_h = (
          datetime.now(timezone.utc) - datetime.fromisoformat(doc["fetched_utc"])
        ).total_seconds() / 3600
        if age_h < 6 and doc.get("pairs"):
          print(f"[universe] Using cached {len(doc['pairs'])} pairs ({age_h:.1f}h old)")
          return doc["pairs"]
    except (json.JSONDecodeError, ValueError, KeyError):
      pass

  pairs = fetch_scanner_pairs(
    n=n,
    quote=quote,
    include_swap=os.environ.get("EW_SCANNER_INCLUDE_SWAP", "1").lower() not in ("0", "false", "no"),
  )
  PAIRS_CACHE.write_text(json.dumps({
    "fetched_utc": _utcnow(),
    "count": n,
    "quote": quote,
    "pairs": pairs,
  }, indent=2))
  return pairs


def _chunk_pairs(pairs: List[str], chunk_size: int, chunk_index: int) -> List[str]:
  if not pairs or chunk_size <= 0:
    return []
  n_chunks = (len(pairs) + chunk_size - 1) // chunk_size
  idx = chunk_index % n_chunks
  start = idx * chunk_size
  return pairs[start : start + chunk_size]


def run_pairs_chunk(
  pairs: List[str],
  tfs: List[str],
  output_dir: str = "output",
  llm_advisory: bool = False,
  llm_advisory_max: int = 3,
) -> List[dict]:
  """Run EW pipeline on a subset of pairs."""
  out = Path(output_dir)
  out.mkdir(parents=True, exist_ok=True)
  ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  chunk_csv = out / "autodream" / f"universe_chunk_{ts}.csv"
  chunk_csv.parent.mkdir(parents=True, exist_ok=True)
  write_pairs_csv(pairs, str(chunk_csv))

  llm_on = llm_advisory or os.environ.get("EW_LLM_ADVISORY", "").lower() in ("1", "true", "yes")
  max_slots = llm_advisory_max if llm_advisory_max else int(os.environ.get("EW_UNIVERSE_LLM_MAX", "3"))

  print(f"\n[universe] Chunk: {len(pairs)} pairs × {tfs} (llm_advisory={llm_on}, max={max_slots})")
  results = run_batch(
    str(chunk_csv), tfs, is_crypto=True,
    llm_advisory=llm_on,
    llm_advisory_max=max_slots,
  )
  return results


def _top_results_for_paper(results: List[dict], max_n: int) -> List[dict]:
  """Limit paper sim to highest-readiness setups when universe is large."""
  if max_n <= 0 or len(results) <= max_n:
    return results

  def rank_key(r: dict) -> float:
    if r.get("status") == "incomplete":
      return -1.0
    setups = (r.get("step8_outcomes") or {}).get("setups") or {}
    best = 0
    for s in setups.values():
      if isinstance(s, dict):
        best = max(best, int(s.get("readiness_score") or 0))
    return float(best)

  ranked = sorted(results, key=rank_key, reverse=True)
  return ranked[:max_n]


def finalize_universe_cycle(
  results: List[dict],
  output_dir: str = "output",
  paper_max: int = 150,
) -> Dict[str, Any]:
  """
  Post-batch enrichment: limit orders, paper P&L, improvement cycle, executive board.
  Runs once per full universe rotation.
  """
  out = Path(output_dir)
  out.mkdir(parents=True, exist_ok=True)
  ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  json_path = out / f"universe_full_{ts}.json"

  paper_targets = _top_results_for_paper(results, paper_max)
  print(f"\n[universe] Finalize cycle — {len(results)} symbols, export on {len(paper_targets)}")

  from engine.accurate_setups import (
    extract_accurate_setups,
    extract_research_setups,
    save_accurate_setups_csv,
    save_research_setups_csv,
  )

  accurate_rows = extract_accurate_setups(results, min_tier="C")
  accurate_csv = out / "latest_accurate_setups.csv"
  save_accurate_setups_csv(accurate_rows, accurate_csv)
  research_rows = extract_research_setups(results)
  research_csv = out / "latest_research_setups.csv"
  save_research_setups_csv(research_rows, research_csv)

  # Executive board runs before export so picks filter limit orders + execution
  executive_board = build_executive_board(results, picks_per_tf=8, max_total=60)
  results = apply_board_to_results(results, executive_board)
  board_paths = save_executive_board(executive_board)

  limit_meta = export_limit_orders(
    paper_targets,
    output_dir=out,
    account_equity=float(os.environ["ACCOUNT_EQUITY"]) if os.environ.get("ACCOUNT_EQUITY") else None,
    usdt_d_pct=float(os.environ["USDT_D_PCT"]) if os.environ.get("USDT_D_PCT") else None,
    board=executive_board,
  )
  print(
    f"[universe] Export: {limit_meta.get('row_count')} rows "
    f"(executive-filtered {limit_meta.get('executive_filtered_rows', 0)})"
  )

  paper_summary: Dict[str, Any] = {}
  if os.environ.get("EW_PAPER_AFTER_BATCH", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.paper_simulator import run_paper_simulation

      paper_summary = run_paper_simulation(
        csv_path=limit_meta.get("latest_csv", str(out / "latest_limit_orders_all_tf.csv")),
        equity_usd=float(os.environ["ACCOUNT_EQUITY"]) if os.environ.get("ACCOUNT_EQUITY") else None,
        fetch_ohlc=True,
      )
      print(
        f"[universe] Paper P&L: ${paper_summary.get('realized_pnl_usd', 0):,.2f} "
        f"({paper_summary.get('simulated', 0)} trades)"
      )
    except Exception as exc:
      print(f"[universe] Paper sim skipped: {exc}")
      paper_summary = {"ok": False, "error": str(exc)}

  improvement: Dict[str, Any] = {}
  if os.environ.get("EW_IMPROVEMENT_CYCLE", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.improvement_cycle import run_improvement_cycle

      rows = list(csv.DictReader(Path(limit_meta["latest_csv"]).open())) if Path(limit_meta["latest_csv"]).exists() else []
      improvement = run_improvement_cycle(
        is_crypto=True,
        record_rows=rows,
        use_llm=False,
        paper=paper_summary,
      )
      print(
        f"[universe] Improvement: resolved={improvement.get('resolved')} "
        f"win_rate={improvement.get('overall_win_rate')}"
      )
    except Exception as exc:
      improvement = {"error": str(exc)}

  deep_research: Dict[str, Any] = {}
  if os.environ.get("EW_DEEP_RESEARCH", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.deep_research import run_deep_research

      symbols = [r.get("symbol") for r in results[:8] if r.get("symbol")]
      deep_research = run_deep_research(symbols=symbols, use_ai=True)
    except Exception as exc:
      deep_research = {"error": str(exc)}

  ai_review: Dict[str, Any] = {}
  if os.environ.get("EW_AI_IMPROVEMENT", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.ai_improvement import run_multi_model_improvement_review

      ai_review = run_multi_model_improvement_review(
        metrics=improvement.get("metrics") if improvement else None,
        board=executive_board,
        paper=paper_summary,
      )
      print(
        f"[universe] AI improvement: {ai_review.get('consensus_stance')} "
        f"({len(ai_review.get('models_consulted') or [])} models, "
        f"escalated={ai_review.get('escalated_to_premium')})"
      )
    except Exception as exc:
      ai_review = {"error": str(exc)}

  picks = executive_board.get("picks", [])
  BEST_TRADES_CSV.parent.mkdir(parents=True, exist_ok=True)
  if picks:
    with BEST_TRADES_CSV.open("w", newline="") as f:
      w = csv.DictWriter(f, fieldnames=list(picks[0].keys()), extrasaction="ignore")
      w.writeheader()
      w.writerows(picks)

  best_trades_meta: Dict[str, Any] = {}
  try:
    from engine.best_trades import export_best_trades

    best_trades_meta = export_best_trades(
      limit_meta.get("latest_csv", str(out / "latest_limit_orders_all_tf.csv")),
      output_dir=out / "v6_scanner",
    )
  except Exception as exc:
    best_trades_meta = {"error": str(exc)}

  execution_result: Dict[str, Any] = {}
  if os.environ.get("EW_UNIVERSE_AUTO_EXECUTE", "0").lower() in ("1", "true", "yes"):
    try:
      from engine.execution_agent import execute_from_csv

      dry = os.environ.get("EW_EXECUTE_CONFIRM", "0") != "1"
      execution_result = execute_from_csv(
        limit_meta.get("latest_csv", str(out / "latest_limit_orders_all_tf.csv")),
        dry_run=dry,
        max_orders=int(os.environ.get("EW_UNIVERSE_MAX_ORDERS", "0")) or 0,
      )
      print(
        f"[universe] Auto-execute: dry_run={execution_result.get('dry_run')} "
        f"submitted={execution_result.get('orders_submitted')}"
      )
    except Exception as exc:
      execution_result = {"ok": False, "error": str(exc)}

  monitor_q = build_monitor_queue(results)
  save_monitor_queue(monitor_q, str(out / "autodream" / "monitor_queue.json"))
  save_batch_json(results, str(json_path))
  save_batch_summary_csv(results, str(out / "latest_universe_summary.csv"))

  return {
    "timestamp_utc": _utcnow(),
    "symbols": len(results),
    "paper_pnl": paper_summary,
    "improvement": improvement,
    "limit_orders_csv": limit_meta.get("latest_csv"),
    "accurate_setups_csv": str(accurate_csv),
    "research_setups_csv": str(research_csv),
    "executive_board_csv": board_paths["csv"],
    "best_trades_csv": str(BEST_TRADES_CSV),
    "best_trades_ranked": best_trades_meta,
    "sqs_ranked_csv": limit_meta.get("sqs_ranked_csv"),
    "sqs": limit_meta.get("sqs"),
    "board_picks": executive_board.get("board_picks"),
    "by_action": executive_board.get("by_action"),
    "by_timeframe": executive_board.get("by_timeframe"),
    "ai_improvement": ai_review,
    "execution": execution_result,
    "executive_filtered_rows": limit_meta.get("executive_filtered_rows", 0),
    "deep_research": deep_research,
    "json": str(json_path),
    "monitor_queue": str(out / "autodream" / "monitor_queue.json"),
  }


def run_universe_tick(
  *,
  universe_size: int = 1000,
  chunk_size: int = 25,
  tfs: Optional[List[str]] = None,
  output_dir: str = "output",
  quote: str = "USDT",
  paper_max: int = 150,
  refresh_pairs: bool = False,
  llm_advisory: bool = False,
  llm_advisory_max: int = 3,
) -> Dict[str, Any]:
  """
  One universe tick:
  1. Load/refresh pair list
  2. Process next chunk through EW pipeline
  3. Merge into rolling results store
  4. On full rotation, finalize (paper + learning + board)
  """
  tfs = tfs or UNIVERSE_TFS
  state = load_state()
  pairs = state.get("pairs") or refresh_universe_pairs(universe_size, quote, force=refresh_pairs)
  if refresh_pairs or len(pairs) != universe_size:
    pairs = refresh_universe_pairs(universe_size, quote, force=True)

  chunk_index = int(state.get("chunk_index", 0))
  cycle = int(state.get("cycle", 0))
  n_chunks = max(1, (len(pairs) + chunk_size - 1) // chunk_size)
  chunk_pairs = _chunk_pairs(pairs, chunk_size, chunk_index)

  print(
    f"\n[universe] Tick — size={universe_size} chunk={chunk_index + 1}/{n_chunks} "
    f"({len(chunk_pairs)} pairs) cycle={cycle}"
  )

  chunk_results = run_pairs_chunk(
    chunk_pairs, tfs, output_dir=output_dir,
    llm_advisory=llm_advisory,
    llm_advisory_max=llm_advisory_max,
  )
  by_symbol = merge_results(load_results(), chunk_results)
  save_results(by_symbol)

  finalize_meta = None
  next_chunk = chunk_index + 1
  if next_chunk >= n_chunks:
    print(f"\n[universe] Full rotation complete — finalizing cycle {cycle + 1}")
    finalize_meta = finalize_universe_cycle(
      list(by_symbol.values()),
      output_dir=output_dir,
      paper_max=paper_max,
    )
    cycle += 1
    next_chunk = 0

  state.update({
    "updated_utc": _utcnow(),
    "universe_size": universe_size,
    "chunk_size": chunk_size,
    "timeframes": tfs,
    "pairs": pairs,
    "chunk_index": next_chunk,
    "cycle": cycle,
    "symbols_scanned": len(by_symbol),
    "last_chunk_pairs": chunk_pairs,
    "last_finalize": finalize_meta,
  })
  save_state(state)

  return {
    "chunk_index": chunk_index,
    "next_chunk_index": next_chunk,
    "n_chunks": n_chunks,
    "chunk_pairs": len(chunk_pairs),
    "symbols_in_store": len(by_symbol),
    "cycle": cycle,
    "finalized": finalize_meta is not None,
    "finalize": finalize_meta,
  }
