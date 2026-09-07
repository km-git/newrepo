"""Tests for superseded PR detection (no GitHub calls)."""

from __future__ import annotations

from engine.pr_superseded import is_monetize_superseded, main_has_monetize_stack


def test_main_has_monetize_stack():
  assert main_has_monetize_stack()


def test_monetize_pr_paths_detected():
  ctx = {
    "files": [
      {"path": "engine/monetize.py"},
      {"path": "tests/test_monetize.py"},
      {"path": "ew_tool.py"},
    ],
  }
  assert is_monetize_superseded(ctx)


def test_tape_to_cloud_package_monetize_detected():
  ctx = {
    "files": [
      {"path": "tape_to_cloud/__init__.py"},
      {"path": "tape_to_cloud/monetize/cli.py"},
      {"path": "tests/test_monetize.py"},
    ],
  }
  assert is_monetize_superseded(ctx)


def test_non_monetize_pr_not_superseded():
  ctx = {
    "files": [
      {"path": "engine/limit_orders_export.py"},
      {"path": "tests/test_limit_orders_export.py"},
    ],
  }
  assert not is_monetize_superseded(ctx)
