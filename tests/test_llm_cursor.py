"""Tests for Cursor LLM backend."""

from __future__ import annotations

import json
from unittest.mock import patch

from engine.llm_backend import advisory_credentials_available, llm_backend
from engine.llm_cursor import call_cursor_advisory, cursor_model_for


def test_llm_backend_defaults_to_cursor_with_key(monkeypatch):
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  monkeypatch.delenv("EW_LLM_BACKEND", raising=False)
  monkeypatch.delenv("OPENAI_API_KEY", raising=False)
  assert llm_backend() == "cursor"


def test_llm_backend_direct_when_forced(monkeypatch):
  monkeypatch.setenv("EW_LLM_BACKEND", "direct")
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  assert llm_backend() == "direct"


def test_cursor_model_mapping(monkeypatch):
  monkeypatch.setenv("EW_LLM_BACKEND", "cursor")
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  assert cursor_model_for("openai", "cheap") == "gpt-5-mini"
  assert cursor_model_for("anthropic", "cheap") == "cursor-grok-4.5-high"
  assert "claude" in cursor_model_for("anthropic", "standard")


@patch("engine.llm_cursor._http")
@patch("engine.llm_cursor._poll_run")
@patch("engine.llm_cursor._archive_agent")
def test_call_cursor_advisory_parses_json(mock_archive, mock_poll, mock_http, monkeypatch):
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  mock_http.return_value = {
    "agent": {"id": "bc-test"},
    "run": {"id": "run-test"},
  }
  mock_poll.return_value = {
    "status": "FINISHED",
    "result": json.dumps(
      {
        "stance": "agree",
        "confidence_adjustment": 0.01,
        "summary": "ok",
        "key_risks": [],
        "sizing_note": "normal",
      }
    ),
    "durationMs": 5000,
  }

  out = call_cursor_advisory("DATA:{}\nJSON:", "composer-2.5")
  assert out["stance"] == "agree"
  assert out["backend"] == "cursor"
  mock_archive.assert_called_once_with("bc-test")


def test_advisory_credentials_cursor_only(monkeypatch):
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  monkeypatch.delenv("OPENAI_API_KEY", raising=False)
  monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
  assert advisory_credentials_available() is True
