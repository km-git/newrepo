"""Tests for LLM backend selection."""

from __future__ import annotations

from engine.llm_backend import bootstrap_llm_env, credentials_hint, cursor_key_source, llm_backend


def test_credentials_hint_cursor(monkeypatch):
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  monkeypatch.delenv("EW_LLM_BACKEND", raising=False)
  assert "CURSOR_API_KEY" in credentials_hint()


def test_bootstrap_sets_cursor_backend(monkeypatch, tmp_path):
  (tmp_path / ".env").write_text("CURSOR_API_KEY=crsr_from_dotenv\n")
  import engine.llm_backend as lb

  monkeypatch.setattr(lb, "_ROOT", tmp_path)
  monkeypatch.delenv("CURSOR_API_KEY", raising=False)
  monkeypatch.delenv("EW_LLM_BACKEND", raising=False)
  lb._BOOTSTRAPPED = False
  out = bootstrap_llm_env()
  assert out["backend"] == "cursor"
  assert out["cursor_key"] is True
  assert cursor_key_source() == "CURSOR_API_KEY"
