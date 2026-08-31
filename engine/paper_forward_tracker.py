"""
Daily paper-forward proof loop — dollar P&L tracking without LLM.

Records one OHLC paper-sim snapshot per UTC day, rolls up 30-day metrics,
and compares tracked win-rate vs realized paper P&L.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LEDGER_PATH = Path(os.environ.get("EW_PAPER_FORWARD_LEDGER", "output/execution/paper_forward_ledger.jsonl"))
STATE_PATH = Path(os.environ.get("EW_PAPER_FORWARD_STATE", "output/execution/paper_forward_state.json"))
REPORT_PATH = Path(os.environ.get("EW_PAPER_FORWARD_REPORT", "reports/PAPER_FORWARD.md"))


def _ledger_path() -> Path:
  return Path(os.environ.get("EW_PAPER_FORWARD_LEDGER", str(LEDGER_PATH)))


def _state_path() -> Path:
  return Path(os.environ.get("EW_PAPER_FORWARD_STATE", str(STATE_PATH)))


def _report_path() -> Path:
  return Path(os.environ.get("EW_PAPER_FORWARD_REPORT", str(REPORT_PATH)))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def _utc_date() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def proof_window_days() -> int:
  return int(os.environ.get("EW_PAPER_PROOF_DAYS", "30"))


def min_proof_days() -> int:
  return int(os.environ.get("EW_PAPER_PROOF_MIN_DAYS", "7"))


def _load_ledger() -> List[dict]:
  path = _ledger_path()
  if not path.exists():
    return []
  rows: List[dict] = []
  for line in path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      rows.append(json.loads(line))
    except json.JSONDecodeError:
      continue
  return rows


def _append_ledger(entry: dict) -> None:
  path = _ledger_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(entry, default=str) + "\n")


def _save_state(state: dict) -> None:
  path = _state_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def record_snapshot(
  paper_summary: dict,
  *,
  tracked_metrics: Optional[dict] = None,
  effectiveness_verdict: Optional[str] = None,
  snapshot_date: Optional[str] = None,
) -> dict:
  """Append daily snapshot (replaces same UTC date if re-run)."""
  today = snapshot_date or _utc_date()
  ledger = _load_ledger()
  ledger = [e for e in ledger if e.get("date") != today]

  entry = {
    "date": today,
    "recorded_at": _utcnow(),
    "starting_equity_usd": paper_summary.get("starting_equity_usd"),
    "ending_equity_usd": paper_summary.get("ending_equity_usd"),
    "realized_pnl_usd": paper_summary.get("realized_pnl_usd"),
    "return_pct": paper_summary.get("return_pct"),
    "sharpe": paper_summary.get("sharpe"),
    "sortino": paper_summary.get("sortino"),
    "profit_factor": paper_summary.get("profit_factor"),
    "max_drawdown_pct": paper_summary.get("max_drawdown_pct"),
    "wins": paper_summary.get("wins"),
    "losses": paper_summary.get("losses"),
    "no_fill": paper_summary.get("no_fill"),
    "simulated": paper_summary.get("simulated"),
    "candidates": paper_summary.get("candidates"),
    "fees_usd": paper_summary.get("fees_usd"),
    "tracked_win_rate": (tracked_metrics or {}).get("overall", {}).get("win_rate"),
    "tracked_decided": (tracked_metrics or {}).get("overall", {}).get("decided"),
    "effectiveness_verdict": effectiveness_verdict,
  }
  ledger.append(entry)

  path = _ledger_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
    "\n".join(json.dumps(e, default=str) for e in ledger) + ("\n" if ledger else ""),
    encoding="utf-8",
  )
  return entry


def rolling_metrics(window_days: Optional[int] = None) -> Dict[str, Any]:
  """Aggregate ledger over rolling window."""
  window_days = window_days or proof_window_days()
  cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%d")
  ledger = [e for e in _load_ledger() if (e.get("date") or "") >= cutoff]

  if not ledger:
    return {"days": 0, "window_days": window_days, "entries": []}

  total_pnl = sum(float(e.get("realized_pnl_usd") or 0) for e in ledger)
  total_wins = sum(int(e.get("wins") or 0) for e in ledger)
  total_losses = sum(int(e.get("losses") or 0) for e in ledger)
  total_sim = sum(int(e.get("simulated") or 0) for e in ledger)
  decided = total_wins + total_losses

  start_eq = float(ledger[0].get("starting_equity_usd") or 0)
  end_eq = float(ledger[-1].get("ending_equity_usd") or 0)
  cum_return_pct = round((end_eq - start_eq) / start_eq * 100.0, 4) if start_eq > 0 else None

  return {
    "window_days": window_days,
    "days": len(ledger),
    "first_date": ledger[0].get("date"),
    "last_date": ledger[-1].get("date"),
    "cumulative_pnl_usd": round(total_pnl, 2),
    "cumulative_return_pct": cum_return_pct,
    "total_wins": total_wins,
    "total_losses": total_losses,
    "win_rate": round(total_wins / decided, 4) if decided else None,
    "total_simulated": total_sim,
    "avg_daily_pnl_usd": round(total_pnl / len(ledger), 2) if ledger else 0.0,
    "entries": ledger,
  }


def evaluate_proof_verdict(metrics: Optional[dict] = None) -> Dict[str, Any]:
  """
  Proof gate — positive cumulative P&L over min days.
  Does NOT require LLM; uses dollar P&L only.
  """
  metrics = metrics or rolling_metrics()
  days = int(metrics.get("days") or 0)
  min_days = min_proof_days()
  pnl = float(metrics.get("cumulative_pnl_usd") or 0)
  wr = metrics.get("win_rate")

  gates: List[Dict[str, Any]] = []
  passed = True

  def _gate(name: str, ok: bool, detail: str) -> None:
    nonlocal passed
    if not ok:
      passed = False
    gates.append({"gate": name, "passed": ok, "detail": detail})

  _gate("min_days", days >= min_days, f"{days}/{min_days} daily snapshots")
  _gate("positive_pnl", pnl > 0, f"cumulative P&L ${pnl:,.2f}")
  if wr is not None:
    _gate("win_rate", wr >= 0.45, f"paper WR {wr:.1%}")

  if days < min_days:
    verdict = "PROOF_PENDING"
  elif passed:
    verdict = "PROOF_GO"
  else:
    verdict = "PROOF_NO_GO"

  return {
    "verdict": verdict,
    "passed": passed,
    "gates": gates,
    "metrics": metrics,
    "min_days": min_days,
  }


def write_forward_report(
  *,
  latest_snapshot: Optional[dict] = None,
  proof: Optional[dict] = None,
  path: Optional[Path] = None,
) -> str:
  path = path or _report_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  proof = proof or evaluate_proof_verdict()
  metrics = proof.get("metrics") or rolling_metrics()
  latest = latest_snapshot or (metrics.get("entries") or [{}])[-1] if metrics.get("entries") else {}

  lines = [
    "# Paper Forward Proof",
    "",
    f"**Updated:** {_utcnow()}  ",
    f"**Proof verdict:** `{proof.get('verdict', 'UNKNOWN')}`  ",
    f"**Window:** {metrics.get('days', 0)} / {metrics.get('window_days', 30)} days  ",
    "",
    "## Rolling summary",
    "",
    "| Metric | Value |",
    "|--------|-------|",
    f"| Cumulative P&L | ${metrics.get('cumulative_pnl_usd', 0):,.2f} |",
    f"| Cumulative return | {metrics.get('cumulative_return_pct', 'n/a')}% |",
    f"| Paper win rate | {metrics.get('win_rate', 'n/a')} |",
    f"| Total simulated | {metrics.get('total_simulated', 0)} |",
    f"| Avg daily P&L | ${metrics.get('avg_daily_pnl_usd', 0):,.2f} |",
    "",
    "## Latest snapshot",
    "",
  ]

  if latest:
    lines.extend([
      f"| Field | Value |",
      f"|-------|-------|",
      f"| Date | {latest.get('date', 'n/a')} |",
      f"| Day P&L | ${latest.get('realized_pnl_usd', 0):,.2f} |",
      f"| Wins / Losses | {latest.get('wins', 0)} / {latest.get('losses', 0)} |",
      f"| Tracked WR | {latest.get('tracked_win_rate', 'n/a')} (n={latest.get('tracked_decided', 0)}) |",
      f"| Effectiveness | {latest.get('effectiveness_verdict', 'n/a')} |",
      "",
    ])

  lines.extend(["## Proof gates", "", "| Gate | Passed | Detail |", "|------|--------|--------|"])
  for g in proof.get("gates") or []:
    mark = "✓" if g.get("passed") else "✗"
    lines.append(f"| {g.get('gate')} | {mark} | {g.get('detail')} |")

  lines.extend([
    "",
    "> LLM-free proof loop · one snapshot per UTC day · staged live only after PROOF_GO",
    f"> Ledger: `{_ledger_path()}`",
  ])
  text = "\n".join(lines) + "\n"
  path.write_text(text, encoding="utf-8")
  return text


def _date_range(window_days: int) -> List[str]:
  """UTC dates from (today - window_days + 1) through today inclusive."""
  today = datetime.now(timezone.utc).date()
  start = today - timedelta(days=window_days - 1)
  dates: List[str] = []
  cursor = start
  while cursor <= today:
    dates.append(cursor.strftime("%Y-%m-%d"))
    cursor += timedelta(days=1)
  return dates


def backfill_paper_forward_window(
  *,
  days: Optional[int] = None,
  fetch_ohlc: bool = True,
  force: bool = False,
  equity_usd: Optional[float] = None,
  csv_path: str = "",
  include_effectiveness: bool = False,
) -> Dict[str, Any]:
  """
  Replay paper simulation for each day in the proof window (point-in-time OHLC).

  Fills missing ledger dates so the 30-day forward loop can complete without
  waiting for calendar time. Existing dates are kept unless ``force=True``.
  """
  window_days = days or proof_window_days()
  dates = _date_range(window_days)
  existing = {e.get("date") for e in _load_ledger()}
  to_run = list(dates) if force else [d for d in dates if d not in existing]

  if force:
    kept = [e for e in _load_ledger() if e.get("date") not in set(dates)]
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      "\n".join(json.dumps(e, default=str) for e in kept) + ("\n" if kept else ""),
      encoding="utf-8",
    )
    existing = {e.get("date") for e in kept}

  result: Dict[str, Any] = {
    "timestamp_utc": _utcnow(),
    "window_days": window_days,
    "dates_total": len(dates),
    "dates_backfilled": 0,
    "dates_skipped": len(dates) - len(to_run),
    "snapshots": [],
    "phases": {},
  }

  if not to_run and not force:
    proof = evaluate_proof_verdict()
    write_forward_report(proof=proof)
    result["proof"] = proof
    result["ok"] = True
    result["message"] = "ledger_complete"
    return result

  skip_resolve = os.environ.get("EW_PAPER_FORWARD_SKIP_RESOLVE", "0").lower() in ("1", "true", "yes")
  tracked: Dict[str, Any] = {}
  if skip_resolve:
    try:
      from engine.outcome_tracker import compute_metrics, load_metrics, save_metrics

      tracked = load_metrics() if load_metrics() else compute_metrics()
      save_metrics(tracked)
      result["phases"]["outcomes"] = {"skipped_resolve": True, **tracked}
    except Exception as exc:
      result["phases"]["outcomes"] = {"error": str(exc)}
  else:
    try:
      from engine.outcome_tracker import run_learning_phase

      result["phases"]["outcomes"] = run_learning_phase(is_crypto=True)
      tracked = result["phases"]["outcomes"] if isinstance(result["phases"]["outcomes"], dict) else {}
    except Exception as exc:
      result["phases"]["outcomes"] = {"error": str(exc)}

  from engine.paper_simulator import run_paper_simulation

  ledger_by_date = {e.get("date"): e for e in _load_ledger()}
  default_equity = float(equity_usd or os.environ.get("ACCOUNT_EQUITY", "50000"))

  latest_snapshot: Optional[dict] = None
  last_paper: Dict[str, Any] = {}
  for day in sorted(to_run):
    prev = (
      datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
      - timedelta(days=1)
    ).strftime("%Y-%m-%d")
    if prev in ledger_by_date:
      day_equity = float(ledger_by_date[prev].get("ending_equity_usd") or default_equity)
    else:
      day_equity = default_equity

    paper = run_paper_simulation(
      csv_path=csv_path,
      equity_usd=day_equity,
      fetch_ohlc=fetch_ohlc,
      as_of=day,
      write_report=False,
    )
    last_paper = paper
    snapshot = record_snapshot(
      paper,
      tracked_metrics=tracked if isinstance(tracked, dict) else None,
      effectiveness_verdict=None,
      snapshot_date=day,
    )
    ledger_by_date[day] = snapshot
    latest_snapshot = snapshot
    result["snapshots"].append({
      "date": day,
      "realized_pnl_usd": paper.get("realized_pnl_usd"),
      "simulated": paper.get("simulated"),
      "skipped_count": paper.get("skipped_count"),
      "wins": paper.get("wins"),
      "losses": paper.get("losses"),
    })
    result["dates_backfilled"] += 1

  if last_paper:
    from engine.paper_simulator import write_paper_pnl_report

    write_paper_pnl_report(last_paper)

  proof = evaluate_proof_verdict()
  write_forward_report(latest_snapshot=latest_snapshot, proof=proof)

  if include_effectiveness:
    try:
      from engine.effectiveness_audit import run_full_effectiveness_audit

      result["phases"]["effectiveness"] = run_full_effectiveness_audit(
        fetch_ohlc=False,
        include_walk_forward=True,
      )
    except Exception as exc:
      result["phases"]["effectiveness"] = {"error": str(exc)}

  state = {
    "last_tick_utc": result["timestamp_utc"],
    "proof_verdict": proof.get("verdict"),
    "cumulative_pnl_usd": proof.get("metrics", {}).get("cumulative_pnl_usd"),
    "days_recorded": proof.get("metrics", {}).get("days"),
    "latest_date": latest_snapshot.get("date") if latest_snapshot else None,
    "backfill": True,
  }
  _save_state(state)

  result["proof"] = proof
  result["state"] = state
  result["ok"] = bool(result["dates_backfilled"]) or result["dates_skipped"] == len(dates)
  return result


def run_paper_forward_tick(
  *,
  fetch_ohlc: bool = True,
  equity_usd: Optional[float] = None,
  csv_path: str = "",
  include_effectiveness: bool = True,
) -> Dict[str, Any]:
  """
  One proof tick (no LLM):
  1. Resolve tracked outcomes
  2. OHLC paper simulation
  3. Effectiveness audit (optional, no extra LLM)
  4. Record daily snapshot + report
  """
  result: Dict[str, Any] = {"timestamp_utc": _utcnow(), "phases": {}}

  skip_resolve = os.environ.get("EW_PAPER_FORWARD_SKIP_RESOLVE", "0").lower() in ("1", "true", "yes")
  if skip_resolve:
    try:
      from engine.outcome_tracker import compute_metrics, load_metrics, save_metrics

      metrics = load_metrics() if load_metrics() else compute_metrics()
      save_metrics(metrics)
      result["phases"]["outcomes"] = {"skipped_resolve": True, **metrics}
    except Exception as exc:
      result["phases"]["outcomes"] = {"error": str(exc)}
  else:
    try:
      from engine.outcome_tracker import run_learning_phase

      result["phases"]["outcomes"] = run_learning_phase(is_crypto=True)
    except Exception as exc:
      result["phases"]["outcomes"] = {"error": str(exc)}

  try:
    from engine.paper_policy import refresh_paper_policy

    result["phases"]["policy"] = refresh_paper_policy()
  except Exception as exc:
    result["phases"]["policy"] = {"error": str(exc)}

  tracked = result["phases"].get("outcomes") or {}

  try:
    from engine.paper_simulator import run_paper_simulation

    paper = run_paper_simulation(
      csv_path=csv_path,
      equity_usd=equity_usd,
      fetch_ohlc=fetch_ohlc,
    )
    result["phases"]["paper"] = {
      "ok": paper.get("ok", True),
      "realized_pnl_usd": paper.get("realized_pnl_usd"),
      "wins": paper.get("wins"),
      "losses": paper.get("losses"),
      "simulated": paper.get("simulated"),
    }
  except Exception as exc:
    result["phases"]["paper"] = {"ok": False, "error": str(exc)}
    paper = {}

  try:
    ending = paper.get("ending_equity_usd")
    if ending is not None:
      from engine.risk_ops import update_equity

      risk_state = update_equity(float(ending))
      result["phases"]["risk_ops"] = {
        "equity_usd": float(ending),
        "drawdown_pct": risk_state.get("drawdown_pct"),
        "halted": risk_state.get("halted"),
      }
  except Exception as exc:
    result["phases"]["risk_ops"] = {"error": str(exc)}

  effectiveness_verdict = None
  if include_effectiveness and os.environ.get("EW_PAPER_FORWARD_SKIP_AUDIT", "0").lower() not in ("1", "true", "yes"):
    try:
      from engine.effectiveness_audit import run_full_effectiveness_audit

      audit = run_full_effectiveness_audit(
        fetch_ohlc=False,
        include_walk_forward=True,
      )
      effectiveness_verdict = audit.get("composite_verdict")
      result["phases"]["effectiveness"] = {
        "composite_verdict": effectiveness_verdict,
        "walk_forward": (audit.get("walk_forward") or {}).get("deployment_gate", {}).get("verdict"),
      }
    except Exception as exc:
      result["phases"]["effectiveness"] = {"error": str(exc)}

  snapshot = record_snapshot(
    paper,
    tracked_metrics=tracked if isinstance(tracked, dict) else None,
    effectiveness_verdict=effectiveness_verdict,
  )
  proof = evaluate_proof_verdict()
  write_forward_report(latest_snapshot=snapshot, proof=proof)

  state = {
    "last_tick_utc": result["timestamp_utc"],
    "proof_verdict": proof.get("verdict"),
    "cumulative_pnl_usd": proof.get("metrics", {}).get("cumulative_pnl_usd"),
    "days_recorded": proof.get("metrics", {}).get("days"),
    "latest_date": snapshot.get("date"),
  }
  _save_state(state)

  result["snapshot"] = snapshot
  result["proof"] = proof
  result["state"] = state
  result["ok"] = paper.get("ok", False) or bool(paper.get("simulated"))
  return result
