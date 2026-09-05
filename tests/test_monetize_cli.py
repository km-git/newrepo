"""CLI integration tests for monetize gates, status, report, and royalty recording.

These tests invoke ``ew_tool.main`` so AccessController / RoyaltyReporter are
exercised on the real command dispatch path (not just the library).
"""

from __future__ import annotations

import json
import sys

import pytest

from ew_tool import main


def _run_main(monkeypatch, argv, *, env=None):
    monkeypatch.setattr(sys, "argv", ["ew_tool.py", *argv])
    if env:
        for key, value in env.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
    main()


def test_monetize_status_default_free(monkeypatch, capsys):
    monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
    _run_main(monkeypatch, ["--monetize-status"])
    out = json.loads(capsys.readouterr().out)
    assert out["license"]["tier"] == "free"
    assert "batch" in out["license"]["denied"]
    assert "single_symbol" in out["license"]["allowed"]


def test_monetize_status_pro(monkeypatch, capsys):
    _run_main(monkeypatch, ["--monetize-status"], env={"EW_LICENSE_TIER": "pro"})
    out = json.loads(capsys.readouterr().out)
    assert out["license"]["tier"] == "pro"
    assert "batch" in out["license"]["allowed"]
    assert "live_execution" in out["license"]["denied"]


def test_monetize_status_enterprise(monkeypatch, capsys):
    _run_main(monkeypatch, ["--monetize-status"], env={"EW_LICENSE_TIER": "enterprise"})
    out = json.loads(capsys.readouterr().out)
    assert out["license"]["tier"] == "enterprise"
    assert out["license"]["denied"] == []
    assert "v6_scanner" in out["license"]["allowed"]


def test_monetize_status_invalid_tier_fails_safe(monkeypatch, capsys):
    _run_main(monkeypatch, ["--monetize-status"], env={"EW_LICENSE_TIER": "garbage"})
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["license"]["tier"] == "free"
    assert out["env_tier_valid"] is False
    assert "garbage" in captured.err
    assert "invalid" in captured.err.lower()


def test_monetize_report_writes_valid_json(monkeypatch, tmp_path, capsys):
    report_path = tmp_path / "system" / "royalty_report.json"
    _run_main(
        monkeypatch,
        ["--monetize-report"],
        env={"EW_ROYALTY_REPORT_PATH": str(report_path), "EW_LICENSE_TIER": "free"},
    )
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert report_path.exists()
    disk = json.loads(report_path.read_text())
    assert disk["usage"]["setups_generated"] == 0
    assert out["usage"]["setups_generated"] == 0
    assert "royalty report saved" in captured.err


def test_batch_blocked_on_free(monkeypatch, capsys):
    monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--batch", "samples/batch_symbols.csv"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "batch" in err
    assert "EW_LICENSE_TIER" in err


def test_brain_status_blocked_on_free(monkeypatch, capsys):
    monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--brain-status"])
    assert exc.value.code == 2
    assert "brain_okf" in capsys.readouterr().err


def test_execute_blocked_on_free(monkeypatch, capsys):
    monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--execute"])
    assert exc.value.code == 2
    assert "paper_execution" in capsys.readouterr().err


def test_execute_live_blocked_on_pro(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--execute-live"], env={"EW_LICENSE_TIER": "pro"})
    assert exc.value.code == 2
    assert "live_execution" in capsys.readouterr().err


def test_v6_scan_blocked_on_free(monkeypatch, capsys):
    monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--v6-scan"])
    assert exc.value.code == 2
    assert "v6_scanner" in capsys.readouterr().err


def test_autonomous_daily_blocked_on_free(monkeypatch, capsys):
    monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--autonomous-daily"])
    assert exc.value.code == 2
    assert "autonomous_daily" in capsys.readouterr().err


def test_brain_status_allowed_on_pro(monkeypatch, capsys):
    import engine.brain_consensus as brain_consensus
    import engine.brain_self_improve as brain_self_improve

    monkeypatch.setattr(brain_consensus, "brain_status", lambda: {"ok": True, "concepts": 0})
    monkeypatch.setattr(brain_self_improve, "improvement_summary", lambda: {"ok": True})
    _run_main(monkeypatch, ["--brain-status"], env={"EW_LICENSE_TIER": "pro"})
    out = json.loads(capsys.readouterr().out)
    assert out["brain"]["ok"] is True


def test_v6_scan_allowed_on_enterprise(monkeypatch, capsys):
    import engine.v6_scanner as v6_scanner

    monkeypatch.setattr(
        v6_scanner,
        "run_v6_chunk_scan",
        lambda: {"ok": True, "chunk_pairs": ["BTC/USDT", "ETH/USDT"]},
    )
    _run_main(
        monkeypatch,
        ["--v6-scan"],
        env={"EW_LICENSE_TIER": "enterprise"},
    )
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True


def test_execute_allowed_on_pro_and_records_royalty(monkeypatch, tmp_path, capsys):
    import engine.execution_agent as execution_agent

    report_path = tmp_path / "royalty.json"
    monkeypatch.setattr(
        execution_agent,
        "execute_from_csv",
        lambda **kwargs: {
            "ok": True,
            "submitted": [{"order": {"symbol": "BTC/USDT", "side": "sell"}}],
        },
    )
    _run_main(
        monkeypatch,
        ["--execute"],
        env={"EW_LICENSE_TIER": "pro", "EW_ROYALTY_REPORT_PATH": str(report_path)},
    )
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    loaded = json.loads(report_path.read_text())
    assert loaded["usage"]["signals_fired"] == 1
    assert loaded["usage"]["tickers_scanned"] == 1
    assert "BTC/USDT" in loaded["detail"]["tickers"]


def test_top_over_50_blocked_on_pro(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--top", "51"], env={"EW_LICENSE_TIER": "pro"})
    assert exc.value.code == 2
    assert "unlimited_batch" in capsys.readouterr().err


def _sample_analysis(symbol: str = "BTC/USDT") -> dict:
    return {
        "symbol": symbol,
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
        "status": "staged_entry",
        "step1_htf_bias": {
            "tf": "1d",
            "state": "choppy",
            "wave_A": {"type": "Up", "magnitude": 1.0, "start": 1.0, "end": 2.0},
            "wave_B_end": 1.5,
            "wave_C_current": 1.6,
            "bias": "neutral",
        },
        "step2_adaptive_pivots": {"1d": {"skip": 3, "monowave_count": 5}},
        "step3_kill_zone": {"price_low": 1.0, "price_high": 2.0, "width_pct": 1.0},
        "step4_harmonic_overlap": [],
        "step5_execution_validation": {"in_zone": False, "passes": False},
        "step2_wave_structure": {
            "1d": {
                "tf": "1d",
                "structure": "abc_correction",
                "direction": "BULL",
                "impulse_valid": False,
                "violations": [],
                "wave_sizes": {},
                "waves_last5": [],
            }
        },
        "step3_c_targets": {"c_target_100": 100.0, "c_direction": "up"},
        "step4_harmonic_scan": {},
        "step6_wave_consensus": {
            "consensus_direction": "BULL",
            "consensus_score": 0.55,
            "agreement_pct": 60.0,
            "conviction": "medium",
            "confidence_boost": 0.02,
            "engines_run": 5,
            "engines_valid": 2,
            "votes": [{
                "engine": "internal_1d",
                "source": "internal",
                "direction": "BULL",
                "valid": True,
                "confidence": 0.8,
                "detail": "test",
            }],
            "divergences": [],
            "github_tools_used": [],
        },
        "step8_outcomes": {
            "honest_summary": {"primary_style": "swing", "primary_status": "monitor", "truth": "test"},
            "setups": {},
            "autodream": {"by_style": {}, "history_entries": 0},
        },
        "trade_setup": {
            "action": "scale_long",
            "entry_zone": [1.4, 1.6],
            "stop_loss": 1.2,
            "take_profit_1": 2.0,
            "confidence": 0.45,
            "reason": "staged fib pathway",
        },
        "executive_decision": {
            "verdict": "STAGED_GO",
            "conviction": "moderate",
            "direction": "BULL",
            "position_size_pct": 100,
            "playbook": "Scale in across fib levels",
            "structural_gaps": [],
            "contingencies": [],
        },
        "honesty_audit": {"hard_cap_applied": True, "executive_mode": True},
        "tool_calls_log": [{"tool": "fetch", "args": "{}", "result_hash": "abc"}],
        "reasoning_trace": "executive staged entry",
    }


def test_single_symbol_tags_and_records(monkeypatch, tmp_path, capsys):
    import engine.adaptive as adaptive

    raw = _sample_analysis()
    report_path = tmp_path / "royalty.json"
    monkeypatch.setattr(adaptive, "adaptive_pipeline", lambda *a, **k: raw)
    _run_main(
        monkeypatch,
        ["--symbol", "BTC/USDT", "--crypto"],
        env={"EW_LICENSE_TIER": "free", "EW_ROYALTY_REPORT_PATH": str(report_path)},
    )
    out = json.loads(capsys.readouterr().out)
    assert "_license" in out
    assert out["_license"]["tier"] == "free"
    loaded = json.loads(report_path.read_text())
    assert loaded["usage"]["setups_generated"] == 1
    assert "BTC/USDT" in loaded["detail"]["setups"]
