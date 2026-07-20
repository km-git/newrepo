"""Pre-execution multi-model consensus — EW engines + optional LLM panel."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from engine.llm_token_saver import (
  ew_bypass_enabled,
  ew_consensus_strong_enough,
  synthetic_panel_from_ew_consensus,
)


def execution_consensus_enabled() -> bool:
  return os.environ.get("EW_EXECUTION_CONSENSUS", "1").lower() not in ("0", "false", "no")


def _row_executive(row: dict) -> dict:
  direction = row.get("direction", "LONG")
  dir_norm = "BULL" if direction == "LONG" else "BEAR" if direction == "SHORT" else direction
  return {
    "verdict": row.get("executive_verdict", "STAGED_GO"),
    "direction": dir_norm,
    "conviction": row.get("honest_execution_tier", "medium"),
    "structural_gaps": [],
  }


def _row_consensus(row: dict) -> dict:
  cons = row.get("consensus", "NEUTRAL")
  if cons in ("LONG", "SHORT"):
    cons = "BULL" if cons == "LONG" else "BEAR"
  return {
    "consensus_direction": cons,
    "agreement_pct": float(row.get("agreement_pct") or 0),
    "engines_valid": int(row.get("engines_valid") or 0),
    "github_tools_used": [],
  }


def _rule_adjustments(row: dict, panel: dict) -> dict:
  """Deterministic risk overlays on top of EW / LLM stance."""
  out = dict(panel)
  stance = out.get("consensus_stance", "unknown")
  notes: List[str] = []

  agreement = float(row.get("agreement_pct") or 0)
  stop_pct = float(row.get("stop_distance_pct") or 0)
  tf = row.get("timeframe", "")
  hist = row.get("hist_action", "")

  if hist == "downgrade":
    stance = "reject"
    notes.append("historical autodream downgrade")
  elif agreement and agreement < 40:
    stance = "reject"
    notes.append(f"EW agreement {agreement:.0f}% < 40%")
  elif stop_pct and tf == "15m" and stop_pct < 0.85:
    stance = "caution" if stance == "agree" else stance
    notes.append(f"15m stop only {stop_pct:.2f}% from WAE (floor 0.85%)")
  elif stop_pct and stop_pct > 8.0:
    stance = "caution" if stance == "agree" else stance
    notes.append(f"wide stop {stop_pct:.1f}%")

  if notes:
    summary = out.get("blended_summary") or out.get("summary") or ""
    out["blended_summary"] = f"{summary} | {'; '.join(notes)}".strip(" |")
  out["consensus_stance"] = stance
  out["rule_notes"] = notes
  return out


def _llm_panel_for_row(row: dict) -> Optional[dict]:
  if os.environ.get("EW_EXECUTION_CONSENSUS_LLM", "1").lower() in ("0", "false", "no"):
    return None
  try:
    from engine.llm_advisor import advisory_credentials_available
    from engine.llm_panel import run_panel
    from engine.brain_consensus import _make_call_provider
  except ImportError:
    return None

  if not advisory_credentials_available():
    return None

  sym = row.get("symbol", "?")
  tf = row.get("timeframe", "?")
  prompt = "\n".join([
    "EXECUTION CONSENSUS — approve paper submission for this GTC limit ladder?",
    'Respond JSON: {"stance":"agree|caution|reject","summary":"...","confidence_adjustment":0.0}',
    "",
    f"symbol={sym} tf={tf} direction={row.get('direction')} verdict={row.get('executive_verdict')}",
    f"wae={row.get('wae')} stop={row.get('stop_loss')} stop_dist_pct={row.get('stop_distance_pct')}",
    f"ew_consensus={row.get('consensus')} agreement_pct={row.get('agreement_pct')}",
    f"dca_splits={row.get('dca_splits_pct')} profile={row.get('dca_profile')}",
    f"notional_usd={row.get('position_notional_usd')} leg1_usd={row.get('leg1_usd')}",
    f"hist_action={row.get('hist_action') or 'none'}",
    "",
    "agree = submit all DCA legs; caution = submit with reduced conviction; reject = block execution",
  ])
  verdict = str(row.get("executive_verdict") or "CONDITIONAL_GO")
  panel = run_panel(prompt, verdict=verdict, conviction="medium", call_provider=_make_call_provider())
  return panel


def review_row(row: dict, *, use_llm: Optional[bool] = None) -> Dict[str, Any]:
  """
  Multi-model consensus for one executable export row.
  Uses LLM panel when API keys exist; otherwise EW synthetic + rule overlays.
  """
  executive = _row_executive(row)
  consensus = _row_consensus(row)
  panel: Dict[str, Any]

  llm_on = use_llm
  if llm_on is None:
    llm_on = os.environ.get("EW_EXECUTION_CONSENSUS_LLM", "1").lower() not in ("0", "false", "no")

  llm_panel = _llm_panel_for_row(row) if llm_on else None
  if llm_panel:
    panel = llm_panel
    panel["intelligence_mode"] = panel.get("intelligence_mode", "ensemble")
  elif ew_bypass_enabled():
    panel = synthetic_panel_from_ew_consensus(executive, consensus)
    panel["intelligence_mode"] = "ew_bypass"
  else:
    panel = {
      "consensus_stance": "caution",
      "blended_summary": "No LLM keys — default caution",
      "consulted": ["rules_only"],
      "intelligence_mode": "rules_only",
    }

  panel = _rule_adjustments(row, panel)
  stance = panel.get("consensus_stance", "unknown")
  block_caution = os.environ.get("EW_EXECUTION_BLOCK_CAUTION", "0").lower() in ("1", "true", "yes")
  allowed = stance == "agree" or (stance == "caution" and not block_caution)

  return {
    "symbol": row.get("symbol"),
    "timeframe": row.get("timeframe"),
    "allowed": allowed,
    "stance": stance,
    "summary": panel.get("blended_summary") or panel.get("summary", ""),
    "panel": panel,
    "mode": panel.get("intelligence_mode"),
    "consulted": panel.get("consulted") or [],
  }


def review_executable_rows(rows: List[dict], *, use_llm: Optional[bool] = None) -> Dict[str, Any]:
  """Review all executable rows; return per-row verdicts + allow list."""
  reviews = [review_row(r, use_llm=use_llm) for r in rows]
  allowed_rows = [r for r, rev in zip(rows, reviews) if rev["allowed"]]
  blocked = [rev for rev in reviews if not rev["allowed"]]
  stances = {}
  for rev in reviews:
    stances[rev["stance"]] = stances.get(rev["stance"], 0) + 1
  return {
    "enabled": execution_consensus_enabled(),
    "total": len(rows),
    "allowed": len(allowed_rows),
    "blocked": len(blocked),
    "stances": stances,
    "reviews": reviews,
    "allowed_rows": allowed_rows,
    "blocked_details": blocked,
  }
