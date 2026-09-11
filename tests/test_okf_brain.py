"""Tests for OKF secondary brain (v0.1 bundle read/write)."""

from __future__ import annotations

import pytest

from engine.okf_brain import (
  append_log,
  ensure_bundle_skeleton,
  parse_concept,
  persist_panel_decision,
  search_concepts,
  write_concept,
)


@pytest.fixture
def brain_dir(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "brain"))
  monkeypatch.setenv("EW_OKF_BRAIN", "1")
  return tmp_path / "brain"


def test_ensure_bundle_skeleton(brain_dir):
  root = ensure_bundle_skeleton()
  assert root.exists()
  assert (root / "index.md").exists()
  assert (root / "log.md").exists()
  assert (root / "consensus").is_dir()
  assert (root / "lessons").is_dir()


def test_write_and_parse_concept(brain_dir):
  path = write_concept(
    "decisions/trading/test.md",
    concept_type="Decision",
    title="BTC GO",
    description="test decision",
    body="# Body\n\nVerdict GO.",
    tags=["trading", "go"],
  )
  assert path.exists()
  meta, body = parse_concept(path)
  assert meta["type"] == "Decision"
  assert meta["title"] == "BTC GO"
  assert "Verdict GO" in body


def test_persist_panel_decision(brain_dir):
  result = persist_panel_decision(
    domain="trading",
    subject="BTC/USDT GO",
    verdict="GO",
    stance="agree",
    panel={"consensus_stance": "agree", "consulted": ["openai"], "blended_summary": "Looks good"},
    executive={"verdict": "GO", "conviction": "high"},
  )
  assert result["persisted"] is True
  hits = search_concepts("BTC", concept_type="Decision")
  assert len(hits) >= 1


def test_search_concepts_by_tag(brain_dir):
  write_concept(
    "lessons/btc/lesson.md",
    concept_type="Lesson",
    title="Tighten stops",
    description="swing: tighten stops on low win rate",
    tags=["btc", "lesson"],
  )
  hits = search_concepts("", tag="btc", limit=5)
  assert any(h["type"] == "Lesson" for h in hits)


def test_append_log(brain_dir):
  ensure_bundle_skeleton()
  append_log("test event")
  log = (brain_dir / "log.md").read_text()
  assert "test event" in log
