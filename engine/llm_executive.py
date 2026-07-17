"""Apply multi-model AI panel consensus to the executive decision."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from engine.llm_panel import apply_panel_to_trade

VERDICT_LADDER = ("STANDBY_ORDERS", "STAGED_GO", "CONDITIONAL_GO", "GO")
VERDICT_INDEX = {v: i for i, v in enumerate(VERDICT_LADDER)}

STATUS_FOR_VERDICT = {
  "GO": "execute",
  "CONDITIONAL_GO": "conditional_execute",
  "STANDBY_ORDERS": "active_monitor",
  "STAGED_GO": "staged_entry",
}

ACTION_PREFIX = {
  "GO": "execute",
  "CONDITIONAL_GO": "conditional",
  "STANDBY_ORDERS": "prepare",
  "STAGED_GO": "scale",
}


def executive_consensus_enabled() -> bool:
  """When true, multi-model panel shapes the final executive verdict (default on with advisory)."""
  raw = os.environ.get("EW_LLM_EXECUTIVE_CONSENSUS", "1").lower().strip()
  return raw not in ("0", "false", "no")


def _verdict_rank(verdict: str) -> int:
  return VERDICT_INDEX.get(verdict, 1)


def _shift_verdict(verdict: str, steps: int) -> str:
  idx = _verdict_rank(verdict)
  new_idx = max(0, min(len(VERDICT_LADDER) - 1, idx + steps))
  return VERDICT_LADDER[new_idx]


def _target_verdict_from_stance(
  draft_verdict: str,
  stance: str,
  escalated: bool = False,
) -> str:
  """
  Map panel consensus stance → final executive verdict.
  agree: endorse draft (upgrade CONDITIONAL→GO if premium tiebreaker agreed)
  caution: one step down
  reject: two steps down
  """
  if stance == "unknown":
    return draft_verdict
  if stance == "agree":
    if draft_verdict == "CONDITIONAL_GO" and escalated:
      return "GO"
    if draft_verdict == "STAGED_GO" and escalated:
      return "CONDITIONAL_GO"
    return draft_verdict
  if stance == "caution":
    return _shift_verdict(draft_verdict, -1)
  if stance == "reject":
    return _shift_verdict(draft_verdict, -2)
  return draft_verdict


def _conviction_from_stance(stance: str, current: str) -> str:
  if stance == "agree":
    return "high" if current in ("high", "medium", "moderate") else current
  if stance == "caution":
    return "medium"
  if stance == "reject":
    return "low"
  return current


def _size_from_stance(stance: str, current: int) -> int:
  if stance == "agree":
    return current
  if stance == "caution":
    return max(25, current // 2)
  if stance == "reject":
    return max(15, min(30, current // 4))
  return current


def _sync_trade_action(trade_setup: dict, verdict: str, direction: str) -> dict:
  trade = dict(trade_setup)
  base = ACTION_PREFIX.get(verdict, "scale")
  side = "long" if direction == "BULL" else "short"
  trade["action"] = f"{base}_{side}"
  return trade


def apply_ai_consensus_to_executive(
  executive: dict,
  trade_setup: dict,
  panel: dict,
  status: str = "",
) -> Tuple[dict, dict, str]:
  """
  Finalize executive decision from multi-model panel consensus.
  Returns (executive, trade_setup, pipeline_status).
  """
  exec_out = dict(executive)
  trade = dict(trade_setup)
  draft_verdict = executive.get("verdict", "STAGED_GO")
  stance = panel.get("consensus_stance", "unknown")
  intel = panel.get("intelligence_panel") or panel
  escalated = bool(intel.get("escalated_to_premium"))
  consulted = panel.get("consulted") or intel.get("consulted") or []

  final_verdict = _target_verdict_from_stance(draft_verdict, stance, escalated)
  direction = executive.get("direction", "BULL")

  exec_out["draft_verdict"] = draft_verdict
  exec_out["verdict"] = final_verdict
  exec_out["verdict_source"] = "ai_consensus"
  exec_out["conviction"] = _conviction_from_stance(stance, str(executive.get("conviction", "medium")))
  exec_out["position_size_pct"] = _size_from_stance(stance, int(executive.get("position_size_pct", 100)))

  gaps = list(executive.get("structural_gaps") or [])
  if stance == "reject":
    gaps.append("AI panel consensus: reject — downgrade applied")
  elif stance == "caution":
    gaps.append("AI panel consensus: caution — reduced conviction/size")
  exec_out["structural_gaps"] = gaps

  exec_out["llm_consensus"] = {
    "stance": stance,
    "consulted": consulted,
    "intelligence_mode": panel.get("intelligence_mode") or intel.get("intelligence_mode"),
    "escalated_to_premium": escalated,
    "disagreement_severity": intel.get("disagreement_severity"),
    "blended_summary": panel.get("blended_summary") or intel.get("blended_summary"),
    "draft_verdict": draft_verdict,
    "final_verdict": final_verdict,
  }

  playbook = executive.get("playbook", "")
  panel_note = panel.get("blended_summary") or ""
  if stance == "agree":
    exec_out["playbook"] = f"{playbook} [AI consensus: agree — {len(consulted)} models]"
  elif stance == "caution":
    exec_out["playbook"] = f"{playbook} [AI consensus: caution — proceed reduced]"
  elif stance == "reject":
    exec_out["playbook"] = f"{playbook} [AI consensus: reject — staged/monitor only]"
  if panel_note:
    exec_out["playbook"] += f" | {panel_note[:200]}"

  trade = _sync_trade_action(trade, final_verdict, direction)
  trade = apply_panel_to_trade(trade, panel)

  new_status = STATUS_FOR_VERDICT.get(final_verdict, status or "staged_entry")
  if final_verdict != draft_verdict:
    trade["reason"] = (
      f"{trade.get('reason', '')} | AI panel {stance}: {draft_verdict}→{final_verdict}"
    ).strip(" |")

  return exec_out, trade, new_status


def apply_ai_consensus_to_decision(decision: dict, panel: dict) -> dict:
  """Apply panel consensus to full executive_decide() output dict."""
  if not executive_consensus_enabled():
    trade = apply_panel_to_trade(decision["trade_setup"], panel)
    out = dict(decision)
    out["trade_setup"] = trade
    return out

  executive, trade, status = apply_ai_consensus_to_executive(
    decision["executive_decision"],
    decision["trade_setup"],
    panel,
    decision.get("status", ""),
  )
  out = dict(decision)
  out["executive_decision"] = executive
  out["trade_setup"] = trade
  out["status"] = status
  return out
