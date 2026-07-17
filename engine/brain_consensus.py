"""Secondary brain orchestrator — multi-model consensus with OKF persistence."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from engine.llm_panel import run_panel
from engine.okf_brain import (
  list_index,
  okf_brain_enabled,
  persist_panel_decision,
  persist_query_answer,
  search_concepts,
)


def brain_consensus_enabled() -> bool:
  return okf_brain_enabled() and os.environ.get("EW_BRAIN_CONSENSUS", "1").lower() not in (
    "0",
    "false",
    "no",
  )


def _mock_call_provider(provider: str, model: str, tier: str, task: str, max_out: int) -> dict:
  """Fallback when no API keys — deterministic stub for dry runs."""
  return {
    "available": True,
    "provider": provider,
    "model": model,
    "stance": "caution",
    "summary": f"[stub] {provider}/{model} reviewed ({task})",
    "confidence_adjustment": 0.0,
  }


def _make_call_provider():
  """Build panel call_provider from llm_advisor when credentials exist."""
  from engine.llm_advisor import advisory_credentials_available
  from engine.llm_backend import llm_backend

  if not advisory_credentials_available():
    return _mock_call_provider

  from engine.llm_advisor import _call_advisory  # noqa: PLC2701

  def call_provider(provider: str, model: str, tier: str, task: str, max_out: int) -> dict:
    prompt = os.environ.get("EW_BRAIN_PROMPT", "")
    return _call_advisory(provider, model, tier, task, max_out, prompt)

  if llm_backend() == "cursor":
    from engine.llm_cursor import call_cursor_provider_advisory

    def call_cursor(provider: str, model: str, tier: str, task: str, max_out: int) -> dict:
      prompt = os.environ.get("EW_BRAIN_PROMPT", "")
      return call_cursor_provider_advisory(
        provider, model, tier, prompt, task=task, max_output=max_out
      )

    return call_cursor

  return call_provider


def _brain_prompt(question: str, context_docs: Optional[list] = None) -> str:
  lines = [
    "SECONDARY BRAIN QUERY — answer from trading/PR/engineering knowledge.",
    "Respond JSON: {\"stance\":\"agree|caution|reject\",\"summary\":\"...\",\"confidence_adjustment\":0.0}",
    "",
    f"QUESTION: {question}",
  ]
  if context_docs:
    lines.extend(["", "RELEVANT MEMORY:"])
    for doc in context_docs[:5]:
      lines.append(f"- [{doc.get('type')}] {doc.get('title')}: {doc.get('description', '')}")
  return "\n".join(lines)


def ask_brain(
  question: str,
  *,
  use_llm: Optional[bool] = None,
  search_memory: bool = True,
) -> Dict[str, Any]:
  """
  Query → retrieve OKF memory → multi-model panel → persist → return verdict.
  """
  llm_on = use_llm if use_llm is not None else os.environ.get("EW_BRAIN_LLM", "1").lower() not in (
    "0",
    "false",
    "no",
  )

  context_docs = search_concepts(question, limit=5) if search_memory else []
  prompt = _brain_prompt(question, context_docs)
  os.environ["EW_BRAIN_PROMPT"] = prompt

  panel: Dict[str, Any] = {"consensus_stance": "unknown", "blended_summary": ""}
  if llm_on:
    call_provider = _make_call_provider()
    panel = run_panel(prompt, verdict="GO", conviction="medium", call_provider=call_provider)
    panel["intelligence_panel"] = {
      k: panel.get(k)
      for k in (
        "intelligence_mode",
        "disagreement",
        "disagreement_severity",
        "escalated_to_premium",
        "consulted",
      )
      if k in panel
    }

  stance = panel.get("consensus_stance", "unknown")
  answer = panel.get("blended_summary") or _synthesize_answer(question, stance, context_docs)
  verdict = _verdict_from_stance(stance)

  persist = {}
  if brain_consensus_enabled():
    persist = persist_query_answer(question, answer, panel, verdict=verdict)

  return {
    "question": question,
    "verdict": verdict,
    "stance": stance,
    "answer": answer,
    "panel": panel,
    "memory_hits": context_docs,
    "okf": persist,
  }


def record_decision(
  *,
  domain: str,
  subject: str,
  verdict: str,
  stance: str,
  panel: Dict[str, Any],
  executive: Optional[Dict[str, Any]] = None,
  context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
  """Persist trading/PR/engine decision to OKF brain when enabled."""
  if not brain_consensus_enabled():
    return {"persisted": False, "reason": "brain consensus disabled"}
  return persist_panel_decision(
    domain=domain,
    subject=subject,
    verdict=verdict,
    stance=stance,
    panel=panel,
    executive=executive,
    context=context,
  )


def brain_status() -> Dict[str, Any]:
  """Summary for CLI — index preview + concept counts."""
  from engine.okf_brain import brain_root, ensure_bundle_skeleton

  root = ensure_bundle_skeleton()
  concepts = search_concepts(limit=1000)
  by_type: Dict[str, int] = {}
  for c in concepts:
    t = c.get("type") or "unknown"
    by_type[t] = by_type.get(t, 0) + 1
  return {
    "root": str(root),
    "enabled": brain_consensus_enabled(),
    "concept_count": len(concepts),
    "by_type": by_type,
    "index_preview": list_index()[:800],
  }


def _verdict_from_stance(stance: str) -> str:
  return {
    "agree": "PROCEED",
    "caution": "CONDITIONAL",
    "reject": "HOLD",
  }.get(stance, "UNKNOWN")


def _synthesize_answer(question: str, stance: str, context_docs: list) -> str:
  parts = [f"Consensus ({stance}) on: {question}"]
  if context_docs:
    parts.append(f"Recalled {len(context_docs)} prior concept(s) from OKF memory.")
  return " ".join(parts)
