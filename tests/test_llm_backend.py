"""Tests for LLM backend selection."""

from __future__ import annotations

from engine.llm_backend import credentials_hint, llm_backend


def test_credentials_hint_cursor(monkeypatch):
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  monkeypatch.delenv("EW_LLM_BACKEND", raising=False)
  assert "CURSOR_API_KEY" in credentials_hint()
