"""Self-improvement loop — autodream lessons + honesty audit → OKF secondary brain."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from engine.brain_consensus import brain_consensus_enabled, record_decision
from engine.okf_brain import (
  append_log,
  ensure_bundle_skeleton,
  okf_brain_enabled,
  search_concepts,
  write_concept,
)


def self_improve_enabled() -> bool:
  return brain_consensus_enabled() and os.environ.get("EW_BRAIN_SELF_IMPROVE", "1").lower() not in (
    "0",
    "false",
    "no",
  )


def collect_autodream_lessons(outcomes: dict) -> List[str]:
  """Extract teachable lessons from autodream per-style analysis."""
  lessons: List[str] = []
  ad = outcomes.get("autodream") or {}
  for style, block in (ad.get("by_style") or {}).items():
    for line in block.get("lessons") or []:
      lessons.append(f"[{style}] {line}")
    wr = block.get("win_rate")
    if wr is not None and not block.get("lessons"):
      lessons.append(f"[{style}] backtest win_rate={wr:.0%} n={block.get('simulated_trades', 0)}")
  return lessons


def collect_honesty_facts(outcomes: dict, honesty_audit: Optional[dict] = None) -> Dict[str, Any]:
  """Compact honesty + abstention facts for memory."""
  hs = outcomes.get("honest_summary") or {}
  audit = honesty_audit or {}
  return {
    "truth": hs.get("truth"),
    "primary_style": hs.get("primary_style"),
    "primary_status": hs.get("primary_status"),
    "primary_direction": hs.get("primary_direction"),
    "full_executable_count": hs.get("full_executable_count", 0),
    "probe_executable_count": hs.get("probe_executable_count", 0),
    "monitor_count": hs.get("monitor_count", 0),
    "not_actionable_count": hs.get("not_actionable_count", 0),
    "executive_verdict": hs.get("executive_verdict"),
    "hard_cap_applied": audit.get("hard_cap_applied"),
    "no_rule_relaxation": audit.get("no_rule_relaxation"),
    "ai_executive_consensus": audit.get("ai_executive_consensus"),
    "structural_gaps": audit.get("structural_gaps_disclosed") or [],
  }


def recall_lessons(symbol: str = "", *, limit: int = 5) -> List[str]:
  """
  Recall prior OKF lessons for symbol (or global) to inform panel consensus.
  Index-first: search Lesson + Improvement concepts.
  """
  if not okf_brain_enabled():
    return []
  ensure_bundle_skeleton()
  hits: List[str] = []
  query = symbol.replace("/", " ").split()[0] if symbol else ""
  for concept_type in ("Lesson", "Improvement"):
    for doc in search_concepts(query, concept_type=concept_type, limit=limit):
      desc = doc.get("description") or doc.get("title") or ""
      if desc and desc not in hits:
        hits.append(desc)
      if len(hits) >= limit:
        return hits
  if symbol and len(hits) < limit:
    sym_tag = symbol.split("/")[0].lower()
    for doc in search_concepts("", tag=sym_tag, limit=limit):
      desc = doc.get("description") or ""
      if desc and desc not in hits:
        hits.append(desc)
  return hits[:limit]


def persist_lesson(
  symbol: str,
  lesson: str,
  *,
  style: str = "",
  source: str = "autodream",
) -> Dict[str, Any]:
  """Write a single Lesson concept."""
  if not self_improve_enabled():
    return {"persisted": False}
  ensure_bundle_skeleton()
  sym_slug = symbol.replace("/", "-").lower()
  ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
  slug = lesson[:40].lower().replace(" ", "-").replace("/", "-")
  tags = ["lesson", source]
  if sym_slug:
    tags.append(sym_slug.split("-")[0])
  if style:
    tags.append(style)
  rel = f"lessons/{sym_slug or 'global'}/{ts}-{slug[:30]}.md"
  write_concept(
    rel,
    concept_type="Lesson",
    title=lesson[:120],
    description=lesson[:200],
    body=f"# {lesson}\n\n**Symbol:** {symbol or 'global'}\n**Source:** {source}\n",
    tags=tags,
    extra={"symbol": symbol, "style": style or None, "source": source},
  )
  return {"persisted": True, "path": rel}


def persist_trading_cycle(
  *,
  symbol: str,
  executive: dict,
  outcomes: dict,
  honesty_audit: dict,
  panel: Optional[dict] = None,
  pipeline_status: str = "",
) -> Dict[str, Any]:
  """
  Close the self-improvement loop for one pipeline run:
  1. Persist autodream lessons as Lesson concepts
  2. Persist honesty + executive snapshot as Improvement concept
  3. Record panel consensus decision when present
  """
  if not self_improve_enabled():
    return {"persisted": False, "reason": "self-improve disabled"}

  ensure_bundle_skeleton()
  sym_slug = symbol.replace("/", "-").lower()
  ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
  lessons = collect_autodream_lessons(outcomes)
  honesty = collect_honesty_facts(outcomes, honesty_audit)
  verdict = executive.get("verdict", "UNKNOWN")
  stance = (panel or {}).get("consensus_stance", "n/a")

  lesson_paths = []
  for lesson in lessons[:8]:
    r = persist_lesson(symbol, lesson, source="autodream")
    if r.get("persisted"):
      lesson_paths.append(r.get("path"))

  imp_body = [
    f"# Improvement cycle — {symbol}",
    "",
    f"**Status:** `{pipeline_status}`",
    f"**Executive:** `{verdict}`",
    f"**Panel stance:** `{stance}`",
    "",
    "## Honesty",
    "",
    f"- **truth:** {honesty.get('truth')}",
    f"- **primary:** {honesty.get('primary_style')} ({honesty.get('primary_status')})",
    f"- **executable:** full={honesty.get('full_executable_count')} probe={honesty.get('probe_executable_count')}",
    f"- **monitor / skip:** {honesty.get('monitor_count')} / {honesty.get('not_actionable_count')}",
    "",
  ]
  if honesty.get("structural_gaps"):
    imp_body.extend(["## Structural gaps", ""])
    for gap in honesty["structural_gaps"][:5]:
      imp_body.append(f"- {gap}")
    imp_body.append("")

  if lessons:
    imp_body.extend(["## Autodream lessons", ""])
    for lesson in lessons:
      imp_body.append(f"- {lesson}")
    imp_body.append("")

  imp_body.extend([
    "## Self-improvement note",
    "",
    "Tracked setups resolve TP/SL → metrics feed gates on next run. "
    "Honesty gates unchanged — only sizing/readiness adjust from history.",
    "",
  ])

  imp_rel = f"improvements/{sym_slug}/{ts}.md"
  write_concept(
    imp_rel,
    concept_type="Improvement",
    title=f"{symbol} {verdict} — {honesty.get('primary_status', 'run')}",
    description=honesty.get("truth", "")[:200],
    body="\n".join(imp_body),
    tags=[sym_slug.split("-")[0], verdict.lower(), honesty.get("primary_status", "run") or "run"],
    extra={
      "symbol": symbol,
      "verdict": verdict,
      "pipeline_status": pipeline_status,
      "lesson_count": len(lessons),
    },
  )

  decision = {}
  if panel and panel.get("consensus_stance"):
    decision = record_decision(
      domain="trading",
      subject=f"{symbol} @ {verdict}",
      verdict=verdict,
      stance=panel.get("consensus_stance", "unknown"),
      panel=panel,
      executive=executive,
      context={"honesty": honesty, "lessons": lessons[:5]},
    )

  append_log(f"Self-improve {symbol}: {verdict} lessons={len(lessons)}")
  return {
    "persisted": True,
    "lessons": lesson_paths,
    "improvement_path": imp_rel,
    "decision": decision,
    "recalled_for_next_run": len(lessons),
  }


def improvement_summary(symbol: str = "") -> Dict[str, Any]:
  """CLI status — lesson/improvement counts."""
  lessons = search_concepts(symbol, concept_type="Lesson", limit=100)
  improvements = search_concepts(symbol, concept_type="Improvement", limit=100)
  return {
    "enabled": self_improve_enabled(),
    "symbol_filter": symbol or None,
    "lesson_count": len(lessons),
    "improvement_count": len(improvements),
    "recent_lessons": [l.get("description") for l in lessons[:5]],
    "recent_improvements": [i.get("title") for i in improvements[:5]],
  }
