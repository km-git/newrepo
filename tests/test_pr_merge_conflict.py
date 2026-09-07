"""Tests for PR merge conflict auto-resolution."""

from __future__ import annotations

from engine.pr_merge_conflict import (
  ConflictHunk,
  _rule_resolve_hunk,
  classify_file_resolution,
  has_conflict_markers,
  parse_conflict_hunks,
  resolve_file_conflicts,
  should_skip_conflict_resolution,
)


SAMPLE_CONFLICT = """\
def foo():
<<<<<<< HEAD
  x = 1
=======
  y = 2
>>>>>>> origin/main
  return x
"""


def test_parse_conflict_hunks():
  hunks = parse_conflict_hunks(SAMPLE_CONFLICT)
  assert len(hunks) == 1
  assert "x = 1" in hunks[0].ours
  assert "y = 2" in hunks[0].theirs


def test_rule_resolve_identical():
  hunk = ConflictHunk("m", "same\n", "same\n")
  merged, strategy = _rule_resolve_hunk(hunk)
  assert merged == "same\n"
  assert strategy == "identical"


def test_rule_resolve_union_imports():
  hunk = ConflictHunk(
    "m",
    "from engine.a import foo\n",
    "from engine.b import bar\n",
  )
  merged, strategy = _rule_resolve_hunk(hunk)
  assert strategy == "union_lines"
  assert "foo" in merged
  assert "bar" in merged


def test_rule_resolve_take_theirs_when_ours_empty():
  hunk = ConflictHunk("m", "", "keep_me\n")
  merged, strategy = _rule_resolve_hunk(hunk)
  assert merged == "keep_me\n"
  assert strategy == "take_theirs"


def test_resolve_file_conflicts_simple():
  content = """\
<<<<<<< HEAD
alpha = 1
=======
beta = 2
>>>>>>> origin/main
"""
  merged, actions = resolve_file_conflicts("test.py", content)
  assert merged is not None
  assert not has_conflict_markers(merged)
  assert classify_file_resolution(actions) == "simple"


def test_skip_conflict_resolution_when_already_mergeable():
  assert should_skip_conflict_resolution({"mergeable": True, "mergeable_state": "unstable"}) == "already_mergeable"


def test_skip_conflict_resolution_while_github_is_computing():
  assert should_skip_conflict_resolution({"mergeable": None, "mergeable_state": "unknown"}) == "mergeable_unknown"
  assert should_skip_conflict_resolution({"mergeable": None}) == "mergeable_unknown"


def test_do_not_skip_dirty_merge_conflicts():
  assert should_skip_conflict_resolution({"mergeable": False, "mergeable_state": "dirty"}) is None


def test_resolve_file_conflicts_same_line_conflict_needs_ai_or_fails():
  content = """\
<<<<<<< HEAD
value = "ours"
=======
value = "theirs"
>>>>>>> origin/main
"""
  merged, actions = resolve_file_conflicts("test.py", content)
  assert merged is None
  assert any(a.get("status") == "unresolved" for a in actions)
