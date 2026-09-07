"""Integrity checks for the tape-to-cloud Cursor prompt artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MDC = ROOT / ".cursor" / "rules" / "tape-to-cloud-build.mdc"
LOOP_MDC = ROOT / ".cursor" / "rules" / "tape-to-cloud-improvement-loop.mdc"
PROMPT = ROOT / "discovery" / "tape-to-cloud" / "cursor-prompt.md"
LOOP_PROMPT = ROOT / "discovery" / "tape-to-cloud" / "continuous-improvement-loop-prompt.md"
INVENTORY = ROOT / "discovery" / "tape-to-cloud" / "free-tool-inventory.md"
INVENTORY_MDC = ROOT / ".cursor" / "rules" / "tape-to-cloud-free-tool-inventory.mdc"
PYPROJECT_DEPS = ROOT / "discovery" / "tape-to-cloud" / "pyproject-dependencies.toml"
USER_RULE = ROOT / "discovery" / "tape-to-cloud" / "user-rule.txt"

MODULES = (
  "audit",
  "analytics",
  "vtl-cloud",
  "restore",
  "disk-ingest",
  "email-extract",
  "email-migrate",
  "tape-duplicate",
  "media-ingest",
  "tape-ops",
  "tape-saas",
  "tape-vault",
  "destroy",
  "llm-corpus",
  "ml-enrich",
  "monetize",
)

NEVER_ESCALATE = (
  "SHA-256 manifest writer",
  "multipart uploader",
  "lifecycle policy sweep",
  "Postgres audit schema",
  "ffmpeg",
  "tesseract",
  "PII scrubber",
  "tokenization sharder",
  "disk-ingest",
  "tape-vault",
  "monetize",
)

STOP_CONDITIONS = (
  "per-token or per-GB cost",
  "license-and-wrap vs re-implement",
  "specific cloud vendor",
  "chain-of-custody manifest schema",
  "WORM retention policy",
)


def _frontmatter_and_body(text: str) -> tuple[dict[str, str], str]:
  assert text.startswith("---\n"), "rule must start with YAML frontmatter"
  rest = text[4:]
  end = rest.index("\n---\n")
  raw, body = rest[:end], rest[end + 5 :]
  meta: dict[str, str] = {}
  for line in raw.splitlines():
    if ":" not in line:
      continue
    key, value = line.split(":", 1)
    meta[key.strip()] = value.strip()
  return meta, body


def test_project_rule_frontmatter_is_agent_requested():
  meta, body = _frontmatter_and_body(MDC.read_text(encoding="utf-8"))
  assert meta["alwaysApply"] == "false"
  assert "95" in meta["description"]
  assert "Max Mode off" in meta["description"]
  assert body.lstrip().startswith("# Tape-to-Cloud Build Rule")


def test_project_rule_maps_all_sixteen_modules():
  text = MDC.read_text(encoding="utf-8")
  for name in MODULES:
    assert f"`{name}`" in text, f"missing module {name}"
  assert text.count("| `") >= 16


def test_project_rule_never_escalate_and_stop_conditions():
  text = MDC.read_text(encoding="utf-8")
  for phrase in NEVER_ESCALATE:
    assert phrase in text, f"never-escalate missing: {phrase}"
  for phrase in STOP_CONDITIONS:
    assert phrase in text, f"stop condition missing: {phrase}"
  assert "Max Mode is **off by default**" in text
  assert "[model used:" in text
  assert "Composer 2.5 Standard" in text
  assert "Composer 2.5 Fast" not in text.split("## Default model selection")[1].split("## Escalate")[0]


def test_user_rule_is_pasteable_ascii():
  text = USER_RULE.read_text(encoding="utf-8")
  assert text.startswith("ROUTING DISCIPLINE")
  assert "Composer 2.5 Standard (not Fast)" in text
  assert "Max Mode is OFF by default" in text
  assert "[model:" in text
  assert "Do not silently re-route" in text
  text.encode("ascii")


def test_prompt_has_numbered_sections_and_ten_references():
  text = PROMPT.read_text(encoding="utf-8")
  for n, title in (
    (1, "The Principle for This Project"),
    (2, "The Model Tier List (September 2026)"),
    (3, "Artifact A"),
    (4, "Artifact B"),
    (5, "One-Time Settings Checklist"),
    (6, "The 30-Day Audit Loop"),
    (7, "Why This Works for This Specific Project"),
    (8, "One-Sentence Takeaway"),
  ):
    assert f"## {n}. {title}" in text, f"missing heading {n}"
  for n in range(1, 11):
    assert f"[{n}]" in text, f"missing citation [{n}]"
  urls = [
    "https://cursor.com/docs/rules",
    "https://forum.cursor.com/t/a-deep-dive-into-cursor-rules-0-45/60721",
    "https://cursor.com/docs/models-and-pricing",
    "https://cursor.com/blog/router",
    "https://www.eigent.ai/blog/cursor-router-model-routing",
    "https://www.verdent.ai/guides/cursor-usage-limits-explained",
    "https://www.gamsgo.com/blog/cursor-pricing",
    "https://www.finout.io/blog/what-happened-to-cursor-pricing-2026-guide-5-cost-cutting-tips",
    "https://developertoolkit.ai/en/cursor-ide/quick-start/essential-configuration/",
  ]
  for url in urls:
    assert url in text, f"missing URL {url}"
  # Prompt embeds the project rule so the copy-paste artifact stays self-contained.
  assert "alwaysApply: false" in text
  assert "tape-to-cloud-build.mdc" in text
  assert MDC.read_text(encoding="utf-8") in text
  assert USER_RULE.read_text(encoding="utf-8").strip() in text


def test_improvement_loop_rule_frontmatter_and_free_tier_stack():
  meta, body = _frontmatter_and_body(LOOP_MDC.read_text(encoding="utf-8"))
  assert meta["alwaysApply"] == "false"
  assert "prek" in meta["description"].lower()
  assert "No Bugbot" in body
  assert "zizmor" in body
  assert "OSV-Scanner" in body
  assert "Monday 9 AM AEST" in body


def test_improvement_loop_prompt_covers_modules_and_bugbot_replacement():
  text = LOOP_PROMPT.read_text(encoding="utf-8")
  assert text.startswith("# Cursor Prompt: Tape-to-Cloud Tool")
  for name in MODULES:
    assert f"`{name}`" in text, f"missing module {name}"
  for tool in ("prek", "Ruff", "zizmor", "OSV-Scanner", "actionlint"):
    assert tool in text
  assert "No Bugbot" in text
  assert "uv run prek run --all-files" in text
  assert "Monday 9 AM AEST review checklist" in text
  text.encode("utf-8")


def test_free_tool_inventory_catalog_structure():
  text = INVENTORY.read_text(encoding="utf-8")
  assert text.startswith("# Expanding the Free-Tool Inventory")
  for n, title in (
    (1, "Two Asks"),
    (2, "MinIO Archival and SeaweedFS Replacement"),
    (7, "Single `pyproject.toml` Install Matrix"),
    (11, "Inventory Summary"),
    (12, "References"),
  ):
    assert f"## {n}. {title}" in text, f"missing section {n}"
  for tool in ("SeaweedFS", "libratom", "DuckDB", "Temporal", "PaddleOCR", "gitleaks", "mhvtl"):
    assert tool in text
  assert "April 25, 2026" in text
  assert "MinIO Community Edition is archived" in text or "MinIO CE" in text
  for n in range(1, 19):
    assert f"[{n}]" in text, f"missing citation [{n}]"
  text.encode("utf-8")


def test_free_tool_inventory_rule_and_deps_matrix():
  meta, body = _frontmatter_and_body(INVENTORY_MDC.read_text(encoding="utf-8"))
  assert meta["alwaysApply"] == "false"
  assert "SeaweedFS" in body
  assert "MinIO" in body
  assert "free-tool-inventory.md" in body
  deps = PYPROJECT_DEPS.read_text(encoding="utf-8")
  assert "[project]" in deps
  assert "duckdb>=" in deps
  assert "temporalio>=" in deps
  assert "libratom>=" in deps


def test_build_rule_recommends_seaweedfs_not_minio():
  text = MDC.read_text(encoding="utf-8")
  assert "SeaweedFS" in text
  assert "April 25, 2026" in text
  assert "MinIO, Ceph" not in text
