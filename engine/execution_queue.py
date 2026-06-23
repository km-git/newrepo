"""Execution queue — merge executive board picks and monitor upgrades."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from engine.calibrated_execution import calibrated_size_pct
from engine.portfolio_manager import approve_candidates, save_portfolio_state

QUEUE_PATH = Path("output/autodream/execution_queue.json")
EXECUTABLE_ACTIONS = frozenset({"EXECUTE_NOW", "EXECUTE_CAUTION"})


def _pick_to_candidate(pick: dict, source: str = "board") -> dict:
  size_base = float(pick.get("position_size_pct") or 50)
  setup_stub = {
    "style": pick.get("style"),
    "execution_tier": pick.get("execution_tier", "none"),
    "indicators": {"active_tokens": (pick.get("tags") or "").split(", ")},
    "indicator_signals": (pick.get("tags") or "").split(", "),
  }
  cal_size, notes = calibrated_size_pct(setup_stub, size_base)
  return {
    "id": f"{pick['symbol']}:{pick.get('style', '')}",
    "symbol": pick["symbol"],
    "style": pick.get("style"),
    "timeframe": pick.get("timeframe"),
    "direction": pick.get("direction"),
    "source": source,
    "executive_action": pick.get("executive_action"),
    "executive_score": pick.get("executive_score"),
    "position_size_pct": size_base,
    "calibrated_size_pct": cal_size,
    "size_notes": notes,
    "execution_tier": pick.get("execution_tier"),
    "pipeline_status": pick.get("pipeline_status"),
    "entry": pick.get("entry"),
    "stop": pick.get("stop_loss"),
    "stop_pct": pick.get("stop_pct"),
    "tp1": pick.get("tp1"),
    "entry_signal": pick.get("entry_signal"),
    "entry_probe": pick.get("entry_probe"),
    "entry_grade": pick.get("entry_grade"),
    "confluence_count": pick.get("confluence_count"),
    "oos_win_rate": pick.get("oos_win_rate"),
    "oos_trades": pick.get("oos_trades"),
    "playbook": pick.get("playbook"),
    "priority": _priority_score(pick),
  }


def _priority_score(row: dict) -> int:
  action_rank = {
    "EXECUTE_NOW": 0,
    "EXECUTE_CAUTION": 1,
    "SCALE_IN": 2,
  }.get(row.get("executive_action", ""), 9)
  smc_bonus = 0 if row.get("style") == "smc" and row.get("entry_signal") else 1
  return action_rank * 1000 + smc_bonus * 100 - int(row.get("executive_score") or 0)


def collect_board_candidates(
  board: dict,
  actions: Optional[frozenset] = None,
) -> List[dict]:
  """Pull EXECUTE_NOW / EXECUTE_CAUTION picks from executive board."""
  actions = actions or EXECUTABLE_ACTIONS
  out: List[dict] = []
  for pick in board.get("picks", []):
    if pick.get("executive_action") not in actions:
      continue
    if pick.get("pipeline_status") not in ("executable", "monitor"):
      continue
    out.append(_pick_to_candidate(pick, source="board"))
  out.sort(key=lambda x: x["priority"])
  return out


def collect_monitor_upgrades_from_events(events: List[dict], queue: List[dict]) -> List[dict]:
  """Build upgrade candidates from monitor scan events + queue geometry."""
  upgraded_keys = {
    (e["symbol"], e["style"])
    for e in events
    if e.get("prior_status") == "monitor" and e.get("new_status") == "executable"
  }
  if not upgraded_keys:
    return []
  items: List[dict] = []
  for item in queue:
    if (item.get("symbol"), item.get("style")) not in upgraded_keys:
      continue
    enriched = dict(item)
    enriched["prior_status"] = "monitor"
    enriched["new_status"] = "executable"
    items.append(enriched)
  return collect_monitor_upgrades(items)


def collect_monitor_upgrades(
  monitor_queue: List[dict],
  since_status: str = "monitor",
) -> List[dict]:
  """Items upgraded monitor→executable since last scan."""
  out: List[dict] = []
  for item in monitor_queue:
    if item.get("prior_status") != since_status:
      continue
    if item.get("new_status") != "executable" and item.get("status") != "executable":
      continue
    size_base = 50 if item.get("execution_tier") == "probe" else 75
    setup_stub = {
      "style": item.get("style"),
      "execution_tier": item.get("execution_tier", "none"),
      "indicator_signals": item.get("indicator_tokens") or item.get("triggers_hit") or [],
      "indicators": {"active_tokens": item.get("indicator_tokens") or []},
    }
    cal_size, notes = calibrated_size_pct(setup_stub, size_base)
    out.append({
      "id": item.get("id") or f"{item['symbol']}:{item.get('style')}",
      "symbol": item["symbol"],
      "style": item.get("style"),
      "timeframe": item.get("check") or item.get("timeframe"),
      "direction": item.get("direction"),
      "source": "monitor_upgrade",
      "executive_action": "EXECUTE_NOW",
      "position_size_pct": size_base,
      "calibrated_size_pct": cal_size,
      "size_notes": notes,
      "execution_tier": item.get("execution_tier"),
      "pipeline_status": "executable",
      "entry": item.get("entry"),
      "stop": item.get("stop"),
      "tp1": item.get("tp1"),
      "entry_signal": item.get("entry_signal"),
      "entry_probe": item.get("entry_probe"),
      "entry_grade": item.get("entry_grade"),
      "confluence_count": item.get("confluence_count"),
      "upgrade_note": item.get("upgrade_note"),
      "priority": 50 if item.get("style") == "smc" else 100,
    })
  out.sort(key=lambda x: x["priority"])
  return out


def build_execution_queue(
  results: Optional[List[dict]] = None,
  board: Optional[dict] = None,
  monitor_queue: Optional[List[dict]] = None,
  *,
  approve: bool = True,
) -> dict:
  """Merge board + monitor upgrades, dedupe, optionally portfolio-approve."""
  candidates: List[dict] = []
  if board:
    candidates.extend(collect_board_candidates(board))
  if monitor_queue:
    candidates.extend(collect_monitor_upgrades(monitor_queue))

  seen: set[str] = set()
  deduped: List[dict] = []
  for c in candidates:
    cid = c.get("id") or f"{c['symbol']}:{c.get('style')}"
    if cid in seen:
      continue
    seen.add(cid)
    deduped.append(c)
  deduped.sort(key=lambda x: x.get("priority", 999))

  approved, rejected = approve_candidates(deduped) if approve else (deduped, [])
  if approve:
    save_portfolio_state(approved, rejected)

  return {
    "updated": datetime.now(timezone.utc).isoformat(),
    "candidate_count": len(candidates),
    "deduped_count": len(deduped),
    "approved_count": len(approved),
    "rejected_count": len(rejected),
    "candidates": deduped,
    "approved": approved,
    "rejected": rejected,
  }


def load_execution_queue(path: Path = QUEUE_PATH) -> dict:
  if not path.exists():
    return {"updated": None, "approved": [], "rejected": []}
  return json.loads(path.read_text())


def save_execution_queue(queue: dict, path: Path = QUEUE_PATH) -> str:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(queue, indent=2, default=str))
  return str(path)
