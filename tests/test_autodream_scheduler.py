"""Tests for autodream scheduler."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine.autodream_scheduler import batch_is_due, publish_latest, save_state, load_state


def test_batch_is_due_when_never_run(tmp_path):
  assert batch_is_due({}, 3600, tmp_path / "missing.json") is True


def test_batch_not_due_within_interval(tmp_path):
  queue = tmp_path / "queue.json"
  queue.write_text("{}")
  recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
  state = {"last_batch_utc": recent}
  assert batch_is_due(state, 3600, queue) is False


def test_batch_due_after_interval(tmp_path):
  queue = tmp_path / "queue.json"
  queue.write_text("{}")
  old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
  state = {"last_batch_utc": old}
  assert batch_is_due(state, 3600, queue) is True


def test_publish_latest_copies_stable_paths(tmp_path):
  src_html = tmp_path / "src.html"
  src_csv = tmp_path / "src.csv"
  src_html.write_text("<html></html>")
  src_csv.write_text("a,b\n1,2\n")
  meta = {
    "timestamp_utc": "2026-01-01T00:00:00+00:00",
    "pairs_count": 2,
    "full_html": str(src_html),
    "full_csv": str(src_csv),
    "setups_csv": str(src_csv),
    "outcomes_csv": str(src_csv),
    "detailed_csv": str(src_csv),
    "json": str(src_csv),
    "monitor_queue": str(src_csv),
    "by_verdict": {"GO": 1},
  }
  latest = publish_latest(meta, output_dir=str(tmp_path))
  assert Path(latest["full_html"]).exists()
  assert (tmp_path / "latest_analysis.html").exists()
  assert (tmp_path / "autodream" / "latest_paths.json").exists()


def test_state_roundtrip(tmp_path):
  p = tmp_path / "state.json"
  save_state({"last_batch_utc": "x"}, p)
  assert load_state(p)["last_batch_utc"] == "x"
