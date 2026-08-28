"""Tests for automated merge conflict resolution."""

from __future__ import annotations

from engine.merge_conflict_resolver import (
  auto_resolve_conflicts_enabled,
  classify_conflict_file,
  has_conflict_markers,
  parse_conflict_hunks,
  resolve_file_conflicts,
  rule_resolve_content,
)


SAMPLE_CONFLICT = """line1
<<<<<<< HEAD
ours_only
=======
>>>>>>> origin/main
line2
"""

SAMPLE_BOTH = """before
<<<<<<< HEAD
alpha = 1
=======
alpha = 1
>>>>>>> origin/main
after
"""

SAMPLE_CODE = """def f():
<<<<<<< HEAD
  return a + b
=======
  return a * b
>>>>>>> origin/main
"""


def test_auto_resolve_enabled_default():
  assert auto_resolve_conflicts_enabled() is True


def test_parse_conflict_hunks():
  hunks = parse_conflict_hunks(SAMPLE_CONFLICT)
  assert len(hunks) == 1
  assert "ours_only" in hunks[0].ours


def test_rule_resolve_one_side_empty():
  resolved, actions = rule_resolve_content("test.py", SAMPLE_CONFLICT)
  assert resolved is not None
  assert not has_conflict_markers(resolved)
  assert "ours_only" in resolved
  assert actions


def test_rule_resolve_identical_sides():
  resolved, _ = rule_resolve_content("test.py", SAMPLE_BOTH)
  assert resolved is not None
  assert "alpha = 1" in resolved


def test_classify_simple_docs():
  info = classify_conflict_file("README.md", SAMPLE_BOTH)
  assert info["classification"] == "simple"


def test_classify_complicated_code():
  info = classify_conflict_file("engine/foo.py", SAMPLE_CODE)
  assert info["classification"] == "complicated"


def test_resolve_file_rules_only():
  result = resolve_file_conflicts("x.py", SAMPLE_BOTH, use_ai=False)
  assert result["status"] == "resolved"
  assert result["method"] == "rules"


def test_resolve_file_fails_without_ai_on_code():
  result = resolve_file_conflicts("engine/foo.py", SAMPLE_CODE, use_ai=False)
  assert result["status"] == "failed"
