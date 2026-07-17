"""Expanded multi-model PR panel — 5/7 approve consensus rule."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Tuple

from engine.llm_model_roster import MODEL
from engine.llm_task_router import max_output_for_task


def pr_panel_size() -> int:
  return int(os.environ.get("EW_PR_PANEL_SIZE", "7"))


def pr_min_approvals() -> int:
  return int(os.environ.get("EW_PR_MIN_APPROVALS", "5"))


def pr_expanded_panel_enabled() -> bool:
  return os.environ.get("EW_PR_EXPANDED_PANEL", "1").lower() not in ("0", "false", "no")


def pr_panel_slots() -> List[Tuple[str, str, str, str]]:
  """
  Specialist slots for PR review (no GPT — per pr-consensus-review.md).
  Returns (provider, model, tier, role).
  """
  slots = [
    ("anthropic", MODEL["opus"], "premium", "architect"),
    ("anthropic", MODEL["fable"], "premium", "hard_architect"),
    ("cursor", MODEL["grok_high"], "standard", "verify"),
    ("composer", MODEL["workhorse_fp"], "cheap", "workhorse"),
    ("cursor", MODEL["screen_alt"], "cheap", "boilerplate"),
    ("openai", MODEL["screen_c"], "cheap", "boilerplate_alt"),
    ("anthropic", MODEL.get("review", MODEL["grok_high"]), "standard", "review"),
  ]
  return slots[: pr_panel_size()]


def tally_votes(responses: List[Dict[str, Any]]) -> Dict[str, int]:
  agrees = sum(1 for r in responses if r.get("stance") == "agree")
  cautions = sum(1 for r in responses if r.get("stance") == "caution")
  rejects = sum(1 for r in responses if r.get("stance") == "reject")
  return {
    "agree": agrees,
    "caution": cautions,
    "reject": rejects,
    "total": agrees + cautions + rejects,
    "panel_size": pr_panel_size(),
    "min_approvals": pr_min_approvals(),
  }


def stance_from_votes(tally: Dict[str, int]) -> str:
  """Approve if >= EW_PR_MIN_APPROVALS (default 5/7) models agree."""
  if tally.get("agree", 0) >= pr_min_approvals():
    return "agree"
  if tally.get("reject", 0) >= 3:
    return "reject"
  if tally.get("caution", 0) >= 3:
    return "caution"
  return "caution"


def run_expanded_pr_panel(
  prompt: str,
  verdict: str,
  conviction: str,
  call_provider: Callable[..., dict],
) -> Dict[str, Any]:
  """Run up to 7 specialist reviewers in parallel; apply 5/7 approve rule."""
  slots = pr_panel_slots()
  max_out = max_output_for_task("screen")
  responses: List[Dict[str, Any]] = []
  routes_meta: List[Dict[str, str]] = []

  def _invoke(slot: Tuple[str, str, str, str]) -> Dict[str, Any]:
    provider, model, tier, role = slot
    task = "architect" if tier == "premium" else ("tiebreaker" if tier == "standard" else "screen")
    resp = call_provider(provider, model, tier, task, max_out)
    resp["role"] = role
    resp["model"] = model
    return resp

  workers = min(len(slots), int(os.environ.get("EW_PR_PANEL_WORKERS", "4")))
  with ThreadPoolExecutor(max_workers=workers) as pool:
    futures = {pool.submit(_invoke, s): s for s in slots}
    for fut in as_completed(futures):
      provider, model, tier, role = futures[fut]
      resp = fut.result()
      responses.append(resp)
      routes_meta.append({"provider": provider, "model": model, "role": role, "stance": resp.get("stance")})

  ok = [r for r in responses if r.get("stance")]
  tally = tally_votes(ok)
  stance = stance_from_votes(tally)
  consulted = [f"{r.get('role')}:{r.get('model')}" for r in ok if r.get("stance")]

  summaries = [f"[{r.get('role')}] {r.get('summary')}" for r in ok if r.get("summary")]

  return {
    "intelligence_mode": "pr_expanded_panel",
    "consensus_stance": stance,
    "vote_tally": tally,
    "consulted": consulted,
    "routes": routes_meta,
    "responses": responses,
    "blended_summary": " | ".join(summaries[:5]) if summaries else "",
    "intelligence_panel": {
      "intelligence_mode": "pr_expanded_panel",
      "consensus_stance": stance,
      "vote_tally": tally,
      "escalated_to_premium": any(s[2] == "premium" for s in slots),
      "disagreement_severity": "hard" if tally.get("reject", 0) >= 3 else ("mild" if stance == "caution" else "none"),
    },
  }
