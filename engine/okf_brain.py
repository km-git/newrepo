"""OKF v0.1 secondary brain — persist and navigate multi-model consensus as concepts."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
  import yaml
except ImportError:  # pragma: no cover
  yaml = None  # type: ignore


OKF_VERSION = "0.1"
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def brain_root() -> Path:
  """OKF bundle root — override with EW_OKF_BRAIN_DIR."""
  raw = os.environ.get("EW_OKF_BRAIN_DIR", "").strip()
  if raw:
    return Path(raw)
  return Path(__file__).resolve().parent.parent / "okf" / "brain"


def okf_brain_enabled() -> bool:
  return os.environ.get("EW_OKF_BRAIN", "1").lower() not in ("0", "false", "no")


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(text: str, max_len: int = 60) -> str:
  slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
  return (slug[:max_len] or "concept").rstrip("-")


def _ensure_yaml() -> None:
  if yaml is None:
    raise RuntimeError("PyYAML required for OKF brain — pip install pyyaml")


def parse_concept(path: Path) -> Tuple[Dict[str, Any], str]:
  """Return (frontmatter dict, markdown body)."""
  text = path.read_text(encoding="utf-8")
  match = FRONTMATTER_RE.match(text)
  if not match:
    return {}, text
  _ensure_yaml()
  meta = yaml.safe_load(match.group(1)) or {}
  body = text[match.end() :]
  return meta, body


def render_concept(frontmatter: Dict[str, Any], body: str) -> str:
  _ensure_yaml()
  fm = dict(frontmatter)
  if "timestamp" not in fm:
    fm["timestamp"] = _utc_now()
  header = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
  body = body.strip()
  return f"---\n{header}\n---\n\n{body}\n"


def write_concept(
  rel_path: str,
  *,
  concept_type: str,
  title: str,
  description: str = "",
  body: str = "",
  tags: Optional[List[str]] = None,
  resource: str = "",
  extra: Optional[Dict[str, Any]] = None,
) -> Path:
  """Write or update an OKF concept file under the brain bundle."""
  root = brain_root()
  path = root / rel_path
  path.parent.mkdir(parents=True, exist_ok=True)

  fm: Dict[str, Any] = {
    "type": concept_type,
    "title": title,
    "description": description,
    "timestamp": _utc_now(),
  }
  if tags:
    fm["tags"] = tags
  if resource:
    fm["resource"] = resource
  if extra:
    fm.update(extra)

  path.write_text(render_concept(fm, body), encoding="utf-8")
  _regenerate_index_for(path.parent)
  if path.parent != root:
    _regenerate_index_for(root)
  return path


def append_log(message: str, *, prefix: str = "Update") -> None:
  """Append newest-first entry to bundle log.md."""
  root = brain_root()
  root.mkdir(parents=True, exist_ok=True)
  log_path = root / "log.md"
  date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
  entry = f"## {date}\n\n**{prefix}:** {message}\n"
  if log_path.exists():
    existing = log_path.read_text(encoding="utf-8")
    log_path.write_text(entry + "\n" + existing, encoding="utf-8")
  else:
    log_path.write_text(f"# Brain Log\n\n{entry}", encoding="utf-8")


def _concept_entries(directory: Path, root: Path) -> List[Tuple[str, str, str]]:
  """List (rel_link, title, description) for concepts in a directory."""
  entries: List[Tuple[str, str, str]] = []
  for child in sorted(directory.iterdir()):
    if child.name in ("index.md", "log.md") or not child.name.endswith(".md"):
      continue
    if child.is_dir():
      rel = child.relative_to(root).as_posix() + "/"
      entries.append((rel, child.name.rstrip("/"), f"Subdirectory {child.name}"))
      continue
    meta, _ = parse_concept(child)
    title = meta.get("title") or child.stem.replace("-", " ").title()
    desc = meta.get("description") or ""
    rel = child.relative_to(directory).as_posix()
    entries.append((rel, title, desc))
  return entries


def _render_index(directory: Path, root: Path, heading: str) -> str:
  entries = _concept_entries(directory, root)
  lines = [f"# {heading}", ""]
  if not entries:
    lines.append("_No concepts yet._")
    lines.append("")
    return "\n".join(lines)
  for rel, title, desc in entries:
    suffix = f" - {desc}" if desc else ""
    lines.append(f"* [{title}]({rel}){suffix}")
  lines.append("")
  return "\n".join(lines)


def _regenerate_index_for(directory: Path) -> None:
  root = brain_root()
  directory.mkdir(parents=True, exist_ok=True)
  rel = directory.relative_to(root)
  if str(rel) == ".":
    heading = "Secondary Brain"
    index_path = root / "index.md"
    body = _render_index(directory, root, heading)
    subdirs = sorted(
      p for p in directory.iterdir() if p.is_dir() and (p / "index.md").exists() or any(p.glob("*.md"))
    )
    if subdirs:
      body = body.rstrip() + "\n\n# Directories\n\n"
      for sub in subdirs:
        if sub.name in ("__pycache__",):
          continue
        meta_path = sub / "index.md"
        desc = ""
        if meta_path.exists():
          idx_body = meta_path.read_text(encoding="utf-8")
          first_line = idx_body.split("\n", 1)[0].lstrip("# ").strip()
          desc = first_line if first_line else sub.name
        body += f"* [{sub.name}/]({sub.name}/) - {desc or sub.name}\n"
      body += "\n"
    index_path.write_text(
      f"---\nokf_version: \"{OKF_VERSION}\"\n---\n\n{body}",
      encoding="utf-8",
    )
    return

  name = str(rel).replace("/", " ").replace("-", " ").title()
  index_path = directory / "index.md"
  index_path.write_text(_render_index(directory, root, name), encoding="utf-8")


def ensure_bundle_skeleton() -> Path:
  """Create bundle root, index, log, and key subdirectories."""
  root = brain_root()
  for sub in ("consensus", "decisions", "queries", "lessons", "improvements"):
    (root / sub).mkdir(parents=True, exist_ok=True)
  _regenerate_index_for(root)
  for sub in ("consensus", "decisions", "queries", "lessons", "improvements"):
    _regenerate_index_for(root / sub)
  log_path = root / "log.md"
  if not log_path.exists():
    log_path.write_text(
      f"# Brain Log\n\n## {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
      "**Creation:** OKF secondary brain bundle initialized.\n",
      encoding="utf-8",
    )
  return root


def list_index(directory: str = "") -> str:
  """Read index.md for progressive disclosure navigation."""
  root = brain_root()
  index_path = root / directory / "index.md" if directory else root / "index.md"
  if not index_path.exists():
    ensure_bundle_skeleton()
    index_path = root / directory / "index.md" if directory else root / "index.md"
  return index_path.read_text(encoding="utf-8")


def search_concepts(
  query: str = "",
  *,
  concept_type: str = "",
  tag: str = "",
  limit: int = 20,
) -> List[Dict[str, Any]]:
  """Scan bundle concepts — simple text/type/tag filter."""
  root = brain_root()
  if not root.exists():
    return []
  q = query.lower().strip()
  results: List[Dict[str, Any]] = []
  for path in sorted(root.rglob("*.md")):
    if path.name in ("index.md", "log.md"):
      continue
    meta, body = parse_concept(path)
    if concept_type and meta.get("type", "").lower() != concept_type.lower():
      continue
    if tag and tag not in (meta.get("tags") or []):
      continue
    haystack = f"{meta.get('title', '')} {meta.get('description', '')} {body}".lower()
    if q and q not in haystack:
      continue
    results.append({
      "path": path.relative_to(root).as_posix(),
      "type": meta.get("type"),
      "title": meta.get("title"),
      "description": meta.get("description"),
      "tags": meta.get("tags", []),
      "timestamp": meta.get("timestamp"),
    })
    if len(results) >= limit:
      break
  return results


def persist_panel_decision(
  *,
  domain: str,
  subject: str,
  verdict: str,
  stance: str,
  panel: Dict[str, Any],
  executive: Optional[Dict[str, Any]] = None,
  context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
  """
  Persist a multi-model consensus outcome as OKF concepts:
  - decisions/<domain>/<slug>.md — final decision
  - consensus/<domain>/<slug>.md — panel audit trail
  """
  if not okf_brain_enabled():
    return {"persisted": False, "reason": "EW_OKF_BRAIN disabled"}

  ensure_bundle_skeleton()
  ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
  slug = _slugify(f"{subject}-{verdict}")[:50]
  domain_slug = _slugify(domain, 30)

  consulted = panel.get("consulted") or []
  summary = panel.get("blended_summary") or panel.get("summary") or ""
  vote_tally = panel.get("vote_tally")

  decision_body = [
    f"# {subject}",
    "",
    f"**Verdict:** `{verdict}`",
    f"**Panel stance:** `{stance}`",
    f"**Domain:** {domain}",
    "",
  ]
  if executive:
    decision_body.append("## Executive")
    for key in ("draft_verdict", "conviction", "position_size_pct", "playbook"):
      if key in executive:
        decision_body.append(f"- **{key}:** {executive[key]}")
    decision_body.append("")

  if summary:
    decision_body.extend(["## Summary", "", summary, ""])

  if context:
    decision_body.extend(["## Context", "", "```json", _json_pretty(context), "```", ""])

  decision_rel = f"decisions/{domain_slug}/{ts}-{slug}.md"
  write_concept(
    decision_rel,
    concept_type="Decision",
    title=f"{subject} → {verdict}",
    description=f"{domain} consensus: {stance} → {verdict}",
    body="\n".join(decision_body),
    tags=[domain_slug, stance, verdict.lower().replace("_", "-")],
    extra={"domain": domain, "verdict": verdict, "stance": stance},
  )

  consensus_lines = [
    f"# Panel consensus — {subject}",
    "",
    f"**Stance:** `{stance}`",
    f"**Consulted:** {', '.join(str(c) for c in consulted) or 'none'}",
    "",
  ]
  if vote_tally:
    consensus_lines.extend([
      "## Vote tally",
      "",
      f"- agree: {vote_tally.get('agree', 0)}",
      f"- caution: {vote_tally.get('caution', 0)}",
      f"- reject: {vote_tally.get('reject', 0)}",
      "",
    ])

  intel = panel.get("intelligence_panel") or panel
  if intel.get("disagreement"):
    consensus_lines.append(f"**Disagreement:** {intel.get('disagreement_severity', 'yes')}")
  if intel.get("escalated_to_premium"):
    consensus_lines.append("**Escalated to premium tiebreaker**")
  consensus_lines.extend(["", "## Panel JSON", "", "```json", _json_pretty(panel), "```", ""])

  consensus_rel = f"consensus/{domain_slug}/{ts}-{slug}.md"
  write_concept(
    consensus_rel,
    concept_type="Consensus",
    title=f"Panel — {subject}",
    description=f"Multi-model consensus ({stance}) for {subject}",
    body="\n".join(consensus_lines),
    tags=[domain_slug, "panel", stance],
    resource=f"../decisions/{domain_slug}/{ts}-{slug}.md",
  )

  append_log(f"{domain}: {subject} → {verdict} (stance={stance})")
  return {
    "persisted": True,
    "decision_path": decision_rel,
    "consensus_path": consensus_rel,
  }


def persist_query_answer(
  question: str,
  answer: str,
  panel: Dict[str, Any],
  *,
  verdict: str = "",
) -> Dict[str, Any]:
  """Persist a brain-ask query and multi-model answer."""
  if not okf_brain_enabled():
    return {"persisted": False, "reason": "EW_OKF_BRAIN disabled"}

  ensure_bundle_skeleton()
  ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
  slug = _slugify(question)[:40]
  stance = panel.get("consensus_stance", "unknown")

  body = [
    f"# {question}",
    "",
    f"**Consensus stance:** `{stance}`",
  ]
  if verdict:
    body.append(f"**Verdict:** `{verdict}`")
  body.extend(["", "## Answer", "", answer, ""])
  if panel.get("blended_summary"):
    body.extend(["## Panel summary", "", panel["blended_summary"], ""])
  body.extend(["## Panel", "", "```json", _json_pretty(panel), "```", ""])

  rel = f"queries/{ts}-{slug}.md"
  write_concept(
    rel,
    concept_type="BrainQuery",
    title=question[:120],
    description=f"Multi-model answer ({stance})",
    body="\n".join(body),
    tags=["query", stance],
    extra={"stance": stance, "verdict": verdict or None},
  )
  append_log(f"Query: {question[:80]} → {stance}")
  return {"persisted": True, "path": rel}


def _json_pretty(obj: Any) -> str:
  import json

  return json.dumps(obj, indent=2, default=str)
