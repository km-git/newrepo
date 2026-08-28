"""Tiered multi-model AI improvement — all Cursor-hosted models, cheap first, escalate when needed."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from cache.disk_cache import get_llm_cache
from engine.brain_consensus import make_prompt_call_provider
from engine.brain_self_improve import persist_lesson, recall_lessons, self_improve_enabled
from engine.llm_advisor import advisory_credentials_available
from engine.llm_backend import llm_backend
from engine.llm_model_roster import MODEL, ROSTER, disagreement_severity, escalate_task_model
from engine.llm_panel import blend_stances, models_disagree, run_panel
from engine.llm_task_router import TaskKind, max_output_for_task, provider_for_task
from engine.model_budget_governor import (
  filter_routes_to_cursor_pro,
  governor_summary,
  is_cursor_pro_model,
  limit_cheap_routes,
  record_model_call,
  should_escalate_to_premium,
  should_use_other_model,
)
from engine.llm_budget_policy import allow_premium_escalation
from engine.token_saver_registry import optimize_prompt_text

NAMESPACE = "ai_improvement"
REVIEW_PATH = Path(os.environ.get("EW_AI_IMPROVEMENT_STATE", "output/system/ai_improvement.json"))


def ai_improvement_enabled() -> bool:
  return os.environ.get("EW_AI_IMPROVEMENT", "1").lower() not in ("0", "false", "no")


def use_all_cursor_models() -> bool:
  """When true, sweep every Cursor Pro first-party model (Composer, Grok)."""
  return os.environ.get("EW_USE_ALL_CURSOR_MODELS", "1").lower() not in ("0", "false", "no")


def use_other_model_pool() -> bool:
  """When true, allow GPT/Claude/Gemini API pool (consumes Other Models quota)."""
  from engine.model_budget_governor import other_model_pool_enabled
  return other_model_pool_enabled()


def cursor_hosted_models() -> List[Dict[str, str]]:
  """
  All models in the Cursor roster that are first-party / cursor-family hosted.
  Sorted cheap → premium for tiered escalation.
  """
  tier_order = {"nano": 0, "workhorse": 1, "standard": 2, "crucial": 3, "flagship": 4}
  hosted = []
  for model_id, meta in ROSTER.items():
    pool = meta.get("pool", "")
    family = meta.get("family", "")
    if pool == "first_party" or family == "cursor":
      hosted.append({
        "model": model_id,
        "tier": meta.get("tier", "workhorse"),
        "pool": pool,
        "family": family,
        "strength": meta.get("strength", ""),
      })
  hosted.sort(key=lambda x: tier_order.get(x["tier"], 9))
  return hosted


def cursor_api_pool_models() -> List[str]:
  """API-pool models reachable via Cursor backend (GPT, Claude, Gemini slots)."""
  if llm_backend() != "cursor":
    return []
  keys = ("nano", "screen_b", "screen_c", "mild_tb", "light_plan", "sol", "opus", "fable")
  return [MODEL[k] for k in keys if MODEL.get(k)]


def improvement_workhorse_routes() -> List[Tuple[str, str, str, TaskKind, int]]:
  """
  Phase 1 — parallel cheap Cursor Pro screens only (Composer, Grok).
  Never uses Other Models — self-improvement stays on Cursor Pro pool.
  """
  task: TaskKind = "workhorse"
  max_out = max_output_for_task(task)
  routes: List[Tuple[str, str, str, TaskKind, int]] = []

  for slot in cursor_hosted_models():
    model = slot["model"]
    provider = provider_for_task(task, model)
    routes.append((provider, model, "cheap", task, max_out))

  if not routes:
    routes.append((provider_for_task(task, MODEL["workhorse_fp"]), MODEL["workhorse_fp"], "cheap", task, max_out))
  return limit_cheap_routes(filter_routes_to_cursor_pro(routes, purpose="self_improvement"))


def improvement_escalation_routes(
  verdict: str = "GO",
  conviction: str = "medium",
  stances: Optional[List[str]] = None,
  metrics_poor: bool = False,
) -> List[Tuple[str, str, str, TaskKind, int]]:
  """
  Phase 2+ — standard review and premium specialists (only when escalation warranted).
  Uses remaining Cursor API pool models not yet consulted.
  """
  sev = disagreement_severity(stances or [])
  routes: List[Tuple[str, str, str, TaskKind, int]] = []

  if sev in ("mild", "hard") or metrics_poor:
    tb_model, _, _ = escalate_task_model("tiebreaker", verdict, conviction, stances)
    task: TaskKind = "tiebreaker"
    routes.append((provider_for_task(task, tb_model), tb_model, "standard", task, max_output_for_task(task)))

  if sev == "hard" or metrics_poor:
    for task_name in ("planning", "synthesis", "architect"):
      task = task_name  # type: ignore[assignment]
      if not allow_premium_escalation(
        task, verdict, conviction, stances, context="self_improvement", metrics_poor=metrics_poor,
      ) and task in ("executive", "architect", "synthesis"):
        continue
      model, _, _ = escalate_task_model(task, verdict, conviction, stances)
      if model in {r[1] for r in routes}:
        continue
      routes.append((provider_for_task(task, model), model, "standard", task, max_output_for_task(task)))

  return filter_routes_to_cursor_pro(routes, purpose="self_improvement")


def _compact_payload(
  metrics: Optional[dict],
  board: Optional[dict],
  paper: Optional[dict],
) -> dict:
  overall = (metrics or {}).get("overall") or {}
  wr = overall.get("win_rate")
  picks = (board or {}).get("picks") or []
  compact_picks = [
    {
      "sym": p.get("symbol"),
      "tf": p.get("timeframe"),
      "act": p.get("executive_action"),
      "sc": p.get("executive_score"),
      "dir": p.get("direction"),
    }
    for p in picks[:12]
  ]
  return {
    "wr": round(wr, 3) if wr is not None else None,
    "decided": overall.get("decided"),
    "open": (metrics or {}).get("open_count"),
    "picks": compact_picks,
    "by_tf": (board or {}).get("by_timeframe"),
    "pnl": (paper or {}).get("realized_pnl_usd") if paper else None,
    "lessons": recall_lessons("GLOBAL", limit=3),
  }


def build_improvement_prompt(
  metrics: Optional[dict] = None,
  board: Optional[dict] = None,
  paper: Optional[dict] = None,
) -> str:
  payload = _compact_payload(metrics, board, paper)
  lines = [
    "TRADING SYSTEM IMPROVEMENT REVIEW",
    'JSON: {"stance":"agree|caution|reject","summary":"...","actions":["..."],"risk_adj":0.0}',
    "agree=maintain/boost; caution=reduce probes; reject=halt new risk",
    "",
    f"DATA:{json.dumps(payload, separators=(',', ':'))}",
    "",
    "JSON:",
  ]
  prompt = "\n".join(lines)
  optimized, meta = optimize_prompt_text(prompt)
  return optimized if meta.get("optimized") else prompt


def _metrics_poor(metrics: Optional[dict]) -> bool:
  if not metrics:
    return False
  wr = (metrics.get("overall") or {}).get("win_rate")
  if wr is not None and wr < 0.52:
    return True
  return (metrics.get("open_count") or 0) > 50 and wr is not None and wr < 0.58


def _invoke_routes(
  routes: List[Tuple[str, str, str, TaskKind, int]],
  prompt: str,
  call_provider: Callable[..., dict],
) -> Dict[str, dict]:
  responses: Dict[str, dict] = {}

  def _run(route: Tuple[str, str, str, TaskKind, int]) -> Tuple[str, dict]:
    provider, model, tier, task, max_out = route
    key = f"{model}:{task}"
    resp = call_provider(provider, model, tier, task, max_out)
    if resp.get("available") and resp.get("stance"):
      record_model_call(tier, model)
    return key, resp

  if len(routes) > 1:
    with ThreadPoolExecutor(max_workers=min(len(routes), 6)) as pool:
      futures = {pool.submit(_run, r): r for r in routes}
      for fut in as_completed(futures):
        key, resp = fut.result()
        responses[key] = resp
  else:
    for route in routes:
      key, resp = _run(route)
      responses[key] = resp
  return responses


def run_multi_model_improvement_review(
  *,
  metrics: Optional[dict] = None,
  board: Optional[dict] = None,
  paper: Optional[dict] = None,
  verdict: str = "GO",
  conviction: str = "medium",
  use_cache: bool = True,
) -> Dict[str, Any]:
  """
  Tiered improvement review using all Cursor-hosted models:
  1. Parallel cheap workhorse sweep (Composer, Grok, Gemini, etc.)
  2. run_panel ensemble tiebreaker on disagreement
  3. Premium escalation (Grok High → Luna/Terra → Sol/Opus/Fable) only when needed
  """
  if not ai_improvement_enabled():
    return {"skipped": True, "reason": "EW_AI_IMPROVEMENT disabled"}

  if not advisory_credentials_available():
    return {"skipped": True, "reason": "no LLM credentials", "stub": True}

  prompt = build_improvement_prompt(metrics, board, paper)
  fp = json.dumps(_compact_payload(metrics, board, paper), sort_keys=True)
  cache_key = ("improvement", fp, verdict, use_all_cursor_models())

  if use_cache:
    cached = get_llm_cache().get(NAMESPACE, *cache_key)
    if cached is not None:
      cached = dict(cached)
      cached["cache_hit"] = True
      return cached

  call_provider = make_prompt_call_provider(prompt)

  # Phase 1: all cheap Cursor-hosted models in parallel
  workhorse_routes = improvement_workhorse_routes()
  workhorse_responses = _invoke_routes(workhorse_routes, prompt, call_provider)
  ok_workhorse = [
    r for r in workhorse_responses.values()
    if r.get("available") and r.get("stance")
  ]
  stances = [r.get("stance") for r in ok_workhorse if r.get("stance")]
  poor = _metrics_poor(metrics)
  unanimous = len(stances) >= 2 and len(set(stances)) == 1 and stances[0] == "agree"

  panel: Dict[str, Any] = {"consensus_stance": stances[0] if unanimous else "caution", "skipped": unanimous}
  if not unanimous:
    panel = run_panel(
      prompt, verdict, conviction, call_provider,
      purpose="self_improvement",
      metrics_poor=poor,
    )

  # Phase 3: premium specialists only on disagreement or poor metrics
  escalation_responses: Dict[str, dict] = {}
  escalated = False
  if not unanimous and (models_disagree(ok_workhorse) or panel.get("disagreement") or poor):
    esc_routes = improvement_escalation_routes(verdict, conviction, stances, metrics_poor=poor)
    if esc_routes:
      escalated = True
      escalation_responses = _invoke_routes(esc_routes, prompt, call_provider)

  ok_esc = [r for r in escalation_responses.values() if r.get("available") and r.get("stance")]
  all_stances = stances + [r.get("stance") for r in ok_esc if r.get("stance")]
  tiebreaker = panel.get("tiebreaker")
  consensus = blend_stances(ok_workhorse + ok_esc, tiebreaker)

  summaries = [r.get("summary") for r in ok_workhorse + ok_esc if r.get("summary")]
  if panel.get("blended_summary"):
    summaries.append(panel["blended_summary"])

  models_used = list(workhorse_responses.keys())
  models_used.extend(escalation_responses.keys())
  if panel.get("consulted"):
    models_used.extend(panel["consulted"])

  result: Dict[str, Any] = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "consensus_stance": consensus,
    "blended_summary": " | ".join(s for s in summaries if s)[:2000],
    "disagreement": models_disagree(ok_workhorse) or bool(panel.get("disagreement")),
    "disagreement_severity": disagreement_severity(all_stances) if all_stances else "none",
    "escalated_to_premium": escalated or panel.get("escalated_to_premium", False),
    "metrics_poor": poor,
    "phase1_workhorse": {
      "routes": [{"model": r[1], "task": r[3]} for r in workhorse_routes],
      "responses": workhorse_responses,
      "models_count": len(workhorse_routes),
    },
    "phase2_panel": panel,
    "phase3_escalation": {
      "responses": escalation_responses,
      "models_count": len(escalation_responses),
    } if escalated else None,
    "cursor_hosted_models": [m["model"] for m in cursor_hosted_models()],
    "models_consulted": models_used,
    "backend": llm_backend(),
    "use_all_cursor_models": use_all_cursor_models(),
    "phase1_unanimous": unanimous,
    "governor": governor_summary(),
    "cache_hit": False,
  }

  if use_cache:
    get_llm_cache().set(NAMESPACE, result, *cache_key)

  _persist_review(result)
  _persist_lessons(result)
  return result


def _persist_review(result: dict) -> None:
  REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
  REVIEW_PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


def _persist_lessons(result: dict) -> None:
  if not self_improve_enabled():
    return
  summary = result.get("blended_summary") or ""
  stance = result.get("consensus_stance", "caution")
  models = len(result.get("models_consulted") or [])
  if summary:
    persist_lesson(
      "GLOBAL",
      f"ai_improvement {stance} ({models} models): {summary[:180]}",
      source="ai_improvement",
    )


def load_ai_improvement_state() -> dict:
  if not REVIEW_PATH.exists():
    return {}
  try:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def improvement_llm_enabled() -> bool:
  return os.environ.get("EW_IMPROVEMENT_LLM", "1").lower() not in ("0", "false", "no")
