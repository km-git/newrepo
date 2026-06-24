"""Execution adapter — paper (and future live) order drain."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from engine.calibrated_execution import validate_execution_gates
from engine.indicator_calibration import enrich_ledger_entry, load_calibration
from engine.paper_trading import append_paper_ledger, paper_trade_setup

EXEC_LOG_PATH = Path("output/autodream/execution_log.jsonl")
DEDUP_PATH = Path("output/autodream/execution_dedup.json")
DEFAULT_DEDUP_HOURS = 24


def _fetch_data(symbol: str, timeframe: str) -> dict:
  from fetchers import fetch

  tfs = list(dict.fromkeys(["15m", "1h", "4h", "1d", timeframe]))
  return fetch(symbol, tfs, is_crypto=True)


def _candidate_setup(candidate: dict) -> dict:
  return {
    "style": candidate.get("style", "swing"),
    "status": candidate.get("pipeline_status", "executable"),
    "execution_tier": candidate.get("execution_tier", "probe"),
    "direction": candidate.get("direction", "LONG"),
    "entry": {"anchor": candidate.get("entry")},
    "stop_loss": {"price": candidate.get("stop")},
    "targets": [{"price": candidate.get("tp1"), "rr": 2.0}] if candidate.get("tp1") else [],
    "indicator_signals": candidate.get("indicator_tokens") or [],
    "entry_signal": candidate.get("entry_signal"),
    "entry_probe": candidate.get("entry_probe"),
    "entry_grade": candidate.get("entry_grade"),
    "confluence_count": candidate.get("confluence_count"),
    "readiness_score": candidate.get("readiness_score"),
    "honest_reason": candidate.get("playbook") or candidate.get("upgrade_note"),
  }


def load_execution_dedup(path: Path = DEDUP_PATH) -> dict:
  if not path.exists():
    return {"ids": {}}
  try:
    return json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return {"ids": {}}


def save_execution_dedup(doc: dict, path: Path = DEDUP_PATH) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(doc, indent=2, default=str))


def recently_executed_ids(hours: int = DEFAULT_DEDUP_HOURS, path: Optional[Path] = None) -> Set[str]:
  """Candidate ids executed within the dedup window."""
  path = path or DEDUP_PATH
  doc = load_execution_dedup(path)
  cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
  out: Set[str] = set()
  for cid, ts in (doc.get("ids") or {}).items():
    try:
      if datetime.fromisoformat(ts) >= cutoff:
        out.add(cid)
    except ValueError:
      continue
  return out


def mark_executed_ids(ids: List[str], path: Optional[Path] = None) -> None:
  doc = load_execution_dedup(path or DEDUP_PATH)
  now = datetime.now(timezone.utc).isoformat()
  doc.setdefault("ids", {})
  for cid in ids:
    doc["ids"][cid] = now
  # prune entries older than 7 days
  cutoff = datetime.now(timezone.utc) - timedelta(days=7)
  doc["ids"] = {
    k: v for k, v in doc["ids"].items()
    if datetime.fromisoformat(v) >= cutoff
  }
  save_execution_dedup(doc, path or DEDUP_PATH)


def filter_fresh_candidates(
  candidates: List[dict],
  *,
  hours: int = DEFAULT_DEDUP_HOURS,
) -> tuple[List[dict], List[dict]]:
  """Split candidates into fresh vs already executed recently."""
  recent = recently_executed_ids(hours=hours)
  fresh: List[dict] = []
  skipped: List[dict] = []
  for c in candidates:
    cid = c.get("id") or f"{c['symbol']}:{c.get('style')}"
    if cid in recent:
      skipped.append({**c, "skip_reason": f"executed_within_{hours}h"})
      continue
    fresh.append(c)
  return fresh, skipped


def preview_execution(candidate: dict) -> dict:
  """Dry-run preview — no fetch, no ledger."""
  return {
    "symbol": candidate["symbol"],
    "style": candidate.get("style"),
    "direction": candidate.get("direction"),
    "timeframe": candidate.get("timeframe"),
    "calibrated_size_pct": candidate.get("calibrated_size_pct"),
    "execution_tier": candidate.get("execution_tier"),
    "source": candidate.get("source"),
    "executive_action": candidate.get("executive_action"),
    "entry_signal": candidate.get("entry_signal"),
    "entry_probe": candidate.get("entry_probe"),
    "available": True,
    "dry_run": True,
  }


def execute_paper(
  candidate: dict,
  data: Optional[dict] = None,
) -> dict:
  """Paper-execute one approved candidate."""
  symbol = candidate["symbol"]
  tf = candidate.get("timeframe") or "15m"
  data = data or _fetch_data(symbol, tf)
  df = data.get(tf)
  if df is None or len(df) < 5:
    return {"symbol": symbol, "available": False, "reason": f"missing {tf}"}

  setup = _candidate_setup(candidate)
  size_pct = float(candidate.get("calibrated_size_pct") or candidate.get("position_size_pct") or 50)
  size_factor = size_pct / 100
  trade = paper_trade_setup(symbol, setup, df, size_override=size_factor)
  trade["execution_source"] = candidate.get("source", "queue")
  trade["calibrated_size_pct"] = size_pct
  trade["timeframe"] = tf
  trade["entry_signal"] = candidate.get("entry_signal")
  trade["entry_probe"] = candidate.get("entry_probe")
  trade["entry_grade"] = candidate.get("entry_grade")
  trade["confluence_count"] = candidate.get("confluence_count")
  trade["executive_action"] = candidate.get("executive_action")
  trade["live_execution"] = True

  cal = load_calibration()
  trade = enrich_ledger_entry(trade, setup, cal)
  return trade


def append_execution_log(events: List[dict], path: Optional[Path] = None) -> None:
  if not events:
    return
  path = path or EXEC_LOG_PATH
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a") as f:
    for e in events:
      f.write(json.dumps(e, default=str) + "\n")


def drain_execution_queue(
  queue: dict,
  *,
  mode: str = "paper",
  max_trades: int = 5,
  dry_run: bool = False,
  dedup_hours: int = DEFAULT_DEDUP_HOURS,
  audit_status: Optional[str] = None,
) -> dict:
  """Execute up to max_trades approved candidates."""
  approved = queue.get("approved", [])
  if audit_status is None:
    audit_status = queue.get("audit_status")
  if not approved:
    return {"executed": 0, "trades": [], "skipped": 0, "dry_run": dry_run}

  fresh, deduped = filter_fresh_candidates(approved, hours=dedup_hours)
  to_run = fresh[:max_trades]

  trades: List[dict] = []
  events: List[dict] = []
  data_cache: Dict[str, dict] = {}
  executed_ids: List[str] = []

  for cand in deduped:
    events.append({
      "ts": datetime.now(timezone.utc).isoformat(),
      "symbol": cand["symbol"],
      "style": cand.get("style"),
      "mode": "dedup",
      "status": "skipped",
      "reason": cand.get("skip_reason"),
    })

  for cand in to_run:
    sym = cand["symbol"]
    cid = cand.get("id") or f"{sym}:{cand.get('style')}"

    setup_check = {
      "style": cand.get("style"),
      "status": cand.get("pipeline_status", "executable"),
      "execution_tier": cand.get("execution_tier"),
      "oos_win_rate": cand.get("oos_win_rate"),
      "oos_trades": cand.get("oos_trades"),
      "entry_confirm_ok": cand.get("entry_confirm_ok"),
      "structure_blocked": cand.get("structure_blocked"),
      "vp_filter_ok": cand.get("vp_filter_ok", True),
      "oos_gate": cand.get("oos_gate"),
      "msb_gate": cand.get("msb_gate"),
    }
    ok, _, gate_reason = validate_execution_gates(setup_check, audit_status=audit_status, stamp=False)
    if not ok:
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "style": cand.get("style"),
        "mode": mode,
        "status": "blocked",
        "reason": gate_reason,
      })
      continue

    if dry_run:
      preview = preview_execution(cand)
      trades.append(preview)
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "style": cand.get("style"),
        "mode": "dry_run",
        "status": "would_execute",
        "size_pct": preview.get("calibrated_size_pct"),
        "source": cand.get("source"),
      })
      continue

    if mode != "paper":
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "mode": mode,
        "status": "skipped",
        "reason": "live mode not enabled",
      })
      continue

    if sym not in data_cache:
      tf = cand.get("timeframe") or "15m"
      data_cache[sym] = _fetch_data(sym, tf)
    trade = execute_paper(cand, data_cache[sym])
    if trade.get("available"):
      trades.append(trade)
      executed_ids.append(cid)
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "style": cand.get("style"),
        "mode": "paper",
        "status": "executed",
        "outcome": trade.get("paper_outcome"),
        "size_pct": trade.get("calibrated_size_pct"),
      })
    else:
      events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": sym,
        "mode": "paper",
        "status": "failed",
        "reason": trade.get("reason"),
      })

  if trades and not dry_run:
    append_paper_ledger(trades)
    mark_executed_ids(executed_ids)
  append_execution_log(events)

  return {
    "executed": len(trades),
    "skipped": len(approved) - len(to_run),
    "dedup_skipped": len(deduped),
    "dry_run": dry_run,
    "trades": trades,
    "events": events,
  }
