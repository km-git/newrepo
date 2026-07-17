"""Tests for token saver library registry."""

from __future__ import annotations

from engine.token_saver_registry import (
  TOKEN_SAVER_LIBRARIES,
  library_status,
  missing_libraries,
  registry_summary,
)


def test_registry_has_core_libraries():
  names = {lib.name for lib in TOKEN_SAVER_LIBRARIES}
  assert "tiktoken" in names
  assert "diskcache" in names
  assert "llm-token-optimizer" in names
  assert "tokenpruner" in names


def test_library_status_shape():
  rows = library_status()
  assert len(rows) == len(TOKEN_SAVER_LIBRARIES)
  assert "installed" in rows[0]
  assert "role" in rows[0]


def test_registry_summary():
  summary = registry_summary()
  assert summary["total_count"] == len(TOKEN_SAVER_LIBRARIES)
  assert "internal" in summary


def test_missing_libraries_subset():
  missing = missing_libraries()
  assert len(missing) <= len(TOKEN_SAVER_LIBRARIES)
