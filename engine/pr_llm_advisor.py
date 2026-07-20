"""Multi-model LLM advisory for PR executive consensus."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from engine.llm_advisor import _call_advisory
from engine.llm_backend import advisory_credentials_available, credentials_hint, llm_backend
from engine.llm_panel import effective_intelligence_mode, run_panel
from engine.llm_token_saver import get_model_budget
from engine.pr_panel import pr_expanded_panel_enabled, run_expanded_pr_panel
from engine.token_saver_registry import optimize_prompt_text

PR_SYSTEM_PROMPT = (
  "PR code reviewer. JSON only: stance(agree|caution|reject), "
  "confidence_adjustment(-0.2..0.2), key_risks[], summary(<=200 chars)."
)


def compact_pr_payload(pr: Dict[str, Any], executive: Dict[str, Any]) -> dict:
  return {
    "pr": pr.get("number"),
    "title": (pr.get("title") or "")[:120],
    "v": executive.get("verdict"),
    "conv": executive.get("conviction"),
    "ci": pr.get("ci", {}).get("pass"),
    "add": pr.get("additions"),
    "del": pr.get("deletions"),
    "files": pr.get("changed_files"),
    "gaps": (executive.get("structural_gaps") or [])[:4],
    "labels": (pr.get("labels") or [])[:5],
    "paths": [f.get("path") for f in (pr.get("files") or [])[:12]],
    "diff": (pr.get("diff") or "")[:8000],
  }


def build_pr_advisory_prompt(pr: Dict[str, Any], executive: Dict[str, Any]) -> str:
  blob = json.dumps(compact_pr_payload(pr, executive), separators=(",", ":"), default=str)
  prompt = f"{PR_SYSTEM_PROMPT}\n\nDATA:{blob}\n\nJSON:"
  optimized, _meta = optimize_prompt_text(prompt)
  return optimized


def get_pr_llm_advisory(
  pr: Dict[str, Any],
  executive: Dict[str, Any],
  *,
  enabled: bool = True,
) -> Optional[Dict[str, Any]]:
  if not enabled:
    return None
  if not advisory_credentials_available():
    return {"skipped_reason": f"No credentials ({credentials_hint()})", "consulted": []}

  verdict = executive.get("verdict", "CONDITIONAL_MERGE")
  conviction = executive.get("conviction", "medium")
  prompt = build_pr_advisory_prompt(pr, executive)
  mode = effective_intelligence_mode()

  def _call(provider, model, tier, task, max_output):
    return _call_advisory(provider, model, tier, task, max_output, prompt)

  if pr_expanded_panel_enabled():
    panel = run_expanded_pr_panel(prompt, verdict, conviction, _call)
    result = {
      "consulted": panel.get("consulted", []),
      "consensus_stance": panel.get("consensus_stance"),
      "vote_tally": panel.get("vote_tally"),
      "intelligence_panel": panel.get("intelligence_panel"),
      "intelligence_mode": panel.get("intelligence_mode"),
      "llm_backend": llm_backend(),
      "blended_summary": panel.get("blended_summary"),
    }
  elif mode in ("ensemble", "dual"):
    panel = run_panel(prompt, verdict, conviction, _call)
    result = {
      "consulted": panel.get("consulted", []),
      "consensus_stance": panel.get("consensus_stance"),
      "confidence_adjustment": panel.get("confidence_adjustment"),
      "intelligence_panel": panel,
      "intelligence_mode": mode,
      "llm_backend": llm_backend(),
      "blended_summary": panel.get("blended_summary"),
    }
  else:
    from engine.llm_task_router import screen_routes, screen_task_for_mode, max_output_for_task

    task = screen_task_for_mode(mode)
    max_out = max_output_for_task(task)
    routes = screen_routes(mode)
    responses = {}
    for provider, model, tier, _task, _out in routes:
      responses[provider] = _call(provider, model, tier, task, max_out)

    ok = [r for r in responses.values() if r.get("stance")]
    stance = "unknown"
    if ok:
      stances = [r.get("stance") for r in ok]
      if any(s == "reject" for s in stances):
        stance = "reject"
      elif all(s == "agree" for s in stances):
        stance = "agree"
      else:
        stance = "caution"

    result = {
      "consulted": list(responses.keys()),
      "consensus_stance": stance,
      "intelligence_mode": mode,
      "llm_backend": llm_backend(),
      "intelligence_panel": {"screen": responses, "intelligence_mode": mode},
    }

  budget = get_model_budget().summary()
  result["model_budgets"] = budget
  return result
