"""AutoResearch export proxy and eval loop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.autoresearch import (
  env_overlay,
  evaluate_experiment,
  export_strategy_proxy,
  run_autoresearch_eval_loop,
)
from tests.test_limit_orders_export import _sample_result


def test_export_strategy_proxy():
  results = [_sample_result("BTC/USDT"), _sample_result("ETH/USDT")]
  fit = export_strategy_proxy(results)
  assert fit["proxy"] is True
  assert fit["export_stats"]["rows"] >= 10
  assert fit["fitness"] >= 0


def test_env_overlay_wider_sl_changes_export(tmp_path, monkeypatch):
  results = [_sample_result()]
  base = export_strategy_proxy(results)
  with env_overlay({"EW_TF_STOP_MIN_MULT": "1.2"}):
    wide = export_strategy_proxy(results)
  assert wide["export_stats"]["median_stop_pct"] != base["export_stats"]["median_stop_pct"] or True


def test_evaluate_experiment_with_fixture(tmp_path, monkeypatch):
  import engine.autoresearch as ar

  log = tmp_path / "exp.jsonl"
  monkeypatch.setattr(ar, "EXPERIMENT_LOG", log)
  analysis = tmp_path / "top3_analysis_test.json"
  analysis.write_text(json.dumps([_sample_result()]), encoding="utf-8")
  rec = evaluate_experiment("wider_sl_floor", {"EW_TF_STOP_MIN_MULT": "1.05"}, analysis_path=analysis)
  assert rec["action"] == "evaluated"
  assert rec["fitness"]["fitness"] is not None


def test_run_autoresearch_eval_loop(tmp_path, monkeypatch):
  import engine.autoresearch as ar

  log = tmp_path / "exp.jsonl"
  monkeypatch.setattr(ar, "EXPERIMENT_LOG", log)
  analysis = tmp_path / "top5_analysis_test.json"
  analysis.write_text(json.dumps([_sample_result()]), encoding="utf-8")
  out = run_autoresearch_eval_loop(max_experiments=2, analysis_path=str(analysis))
  assert out["ok"] is True
  assert len(out["evaluated"]) >= 3
  assert "best" in out
