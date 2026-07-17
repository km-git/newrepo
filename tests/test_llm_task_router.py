"""Tests for task-aware LLM routing."""

from __future__ import annotations

from engine.llm_task_router import (
  max_output_for_task,
  routing_matrix,
  screen_routes,
  tiebreaker_task,
  tiebreaker_route,
)


def test_workhorse_smaller_output_than_executive():
  assert max_output_for_task("workhorse") < max_output_for_task("executive")
  assert max_output_for_task("screen") < max_output_for_task("architect")


def test_tiebreaker_task_executive_for_go_high():
  assert tiebreaker_task("GO", "high") == "executive"
  assert tiebreaker_task("CONDITIONAL_GO", "medium") == "planning"


def test_screen_routes_single_is_workhorse(monkeypatch):
  monkeypatch.setenv("EW_LLM_BACKEND", "cursor")
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  routes = screen_routes("single")
  assert len(routes) == 1
  assert routes[0][3] == "workhorse"


def test_screen_routes_ensemble_dual_cheap(monkeypatch):
  monkeypatch.setenv("EW_LLM_BACKEND", "cursor")
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  routes = screen_routes("ensemble")
  assert len(routes) == 2
  assert all(r[2] == "cheap" for r in routes)
  assert all(r[3] == "screen" for r in routes)


def test_tiebreaker_route_premium(monkeypatch):
  monkeypatch.setenv("EW_LLM_BACKEND", "cursor")
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  route = tiebreaker_route("GO", "high")
  assert route is not None
  assert route[2] == "premium"
  assert route[3] == "executive"


def test_routing_matrix_has_token_savers(monkeypatch):
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  matrix = routing_matrix()
  assert matrix["backend"] == "cursor"
  assert len(matrix["tasks"]) >= 7
  assert any("cache" in s.lower() for s in matrix["token_savers"])
