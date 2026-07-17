"""Tests for GPT usage policy — limit not block."""

from __future__ import annotations

from engine.llm_gpt_policy import (
  gpt_replacement_for,
  is_gpt_model,
  minimize_gpt_enabled,
  session_token_limit,
)


def test_session_token_limit_default():
  assert session_token_limit() == 10000


def test_session_token_limit_override(monkeypatch):
  monkeypatch.setenv("EW_LLM_MAX_SESSION_TOKENS", "5000")
  assert session_token_limit() == 5000


def test_minimize_gpt_default_off():
  assert minimize_gpt_enabled() is False


def test_minimize_gpt_can_enable(monkeypatch):
  monkeypatch.setenv("EW_MINIMIZE_GPT", "1")
  assert minimize_gpt_enabled() is True


def test_is_gpt_model():
  assert is_gpt_model("gpt-5-mini") is True
  assert is_gpt_model("composer-2.5") is False


def test_gpt_allowed_by_default(monkeypatch):
  monkeypatch.setenv("EW_MINIMIZE_GPT", "0")
  assert gpt_replacement_for("screen_b", "gpt-5-mini") == "gpt-5-mini"


def test_gpt_replacement_when_preference_on(monkeypatch):
  monkeypatch.setenv("EW_MINIMIZE_GPT", "1")
  assert gpt_replacement_for("screen_b", "gpt-5-mini") == "composer-2.5"
