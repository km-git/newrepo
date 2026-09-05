"""Tests for engine/monetize.py — MonetizationService."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from engine.monetize import (
    AccessDeniedError,
    FEATURE_GATES,
    MonetizationService,
    MonetizationTier,
    monetize_status,
    revenue_estimate,
    usage_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _service(tier: str | None = None, tmp_path: Path | None = None) -> MonetizationService:
    """Create a MonetizationService wired to a temp usage-log file."""
    t = MonetizationTier(tier) if tier else None
    log = tmp_path / "usage_log.jsonl" if tmp_path else Path(tempfile.mktemp(suffix=".jsonl"))
    return MonetizationService(tier=t, usage_log_path=log)


# ---------------------------------------------------------------------------
# Tier detection
# ---------------------------------------------------------------------------

class TestTierDetection:
    def test_default_is_free(self, monkeypatch):
        monkeypatch.delenv("EW_TIER", raising=False)
        svc = _service()
        assert svc.get_tier() == MonetizationTier.FREE

    def test_env_pro(self, monkeypatch):
        monkeypatch.setenv("EW_TIER", "pro")
        svc = _service()
        assert svc.get_tier() == MonetizationTier.PRO

    def test_env_enterprise(self, monkeypatch):
        monkeypatch.setenv("EW_TIER", "enterprise")
        svc = _service()
        assert svc.get_tier() == MonetizationTier.ENTERPRISE

    def test_env_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("EW_TIER", "PRO")
        svc = _service()
        assert svc.get_tier() == MonetizationTier.PRO

    def test_invalid_env_falls_back_to_free(self, monkeypatch):
        monkeypatch.setenv("EW_TIER", "premium_ultra")
        svc = _service()
        assert svc.get_tier() == MonetizationTier.FREE

    def test_constructor_tier_overrides_env(self, monkeypatch):
        monkeypatch.setenv("EW_TIER", "free")
        svc = _service(tier="enterprise")
        assert svc.get_tier() == MonetizationTier.ENTERPRISE

    def test_tier_rank_ordering(self):
        assert MonetizationTier.FREE < MonetizationTier.PRO
        assert MonetizationTier.PRO < MonetizationTier.ENTERPRISE
        assert MonetizationTier.ENTERPRISE >= MonetizationTier.ENTERPRISE
        assert MonetizationTier.FREE <= MonetizationTier.FREE


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

class TestAccessControl:
    def test_free_tier_allows_free_feature(self, tmp_path):
        svc = _service("free", tmp_path)
        assert svc.check_access("analyze_single") is True

    def test_free_tier_denies_pro_feature(self, tmp_path):
        svc = _service("free", tmp_path)
        with pytest.raises(AccessDeniedError) as exc_info:
            svc.check_access("all_timeframes")
        err = exc_info.value
        assert err.feature == "all_timeframes"
        assert err.current == MonetizationTier.FREE
        assert err.required == MonetizationTier.PRO

    def test_free_tier_denies_enterprise_feature(self, tmp_path):
        svc = _service("free", tmp_path)
        with pytest.raises(AccessDeniedError):
            svc.check_access("execute_live")

    def test_pro_allows_pro_feature(self, tmp_path):
        svc = _service("pro", tmp_path)
        assert svc.check_access("all_timeframes") is True
        assert svc.check_access("export_csv") is True

    def test_pro_denies_enterprise_feature(self, tmp_path):
        svc = _service("pro", tmp_path)
        with pytest.raises(AccessDeniedError) as exc_info:
            svc.check_access("execute_live")
        assert exc_info.value.required == MonetizationTier.ENTERPRISE

    def test_enterprise_allows_everything(self, tmp_path):
        svc = _service("enterprise", tmp_path)
        for feature in FEATURE_GATES:
            assert svc.check_access(feature) is True

    def test_has_access_non_raising(self, tmp_path):
        svc = _service("free", tmp_path)
        assert svc.has_access("analyze_single") is True
        assert svc.has_access("v6_scanner") is False

    def test_unknown_feature_treated_as_free(self, tmp_path):
        svc = _service("free", tmp_path)
        assert svc.check_access("totally_unknown_feature_xyz") is True

    def test_available_features_free(self, tmp_path):
        svc = _service("free", tmp_path)
        available = svc.available_features()
        assert "analyze_single" in available
        assert "all_timeframes" not in available
        assert "execute_live" not in available

    def test_available_features_enterprise_has_all(self, tmp_path):
        svc = _service("enterprise", tmp_path)
        available = svc.available_features()
        for feature in FEATURE_GATES:
            assert feature in available

    def test_locked_features_free(self, tmp_path):
        svc = _service("free", tmp_path)
        locked = svc.locked_features()
        assert "all_timeframes" in locked
        assert "execute_live" in locked
        assert "analyze_single" not in locked

    def test_locked_features_enterprise_empty(self, tmp_path):
        svc = _service("enterprise", tmp_path)
        assert svc.locked_features() == []

    def test_access_denied_error_message(self, tmp_path):
        svc = _service("free", tmp_path)
        with pytest.raises(AccessDeniedError) as exc_info:
            svc.check_access("batch_unlimited")
        msg = str(exc_info.value)
        assert "enterprise" in msg
        assert "EW_TIER=enterprise" in msg


# ---------------------------------------------------------------------------
# Usage logging
# ---------------------------------------------------------------------------

class TestUsageLogging:
    def test_log_creates_file(self, tmp_path):
        svc = _service("pro", tmp_path)
        svc.log_usage("BTC/USDT", "1h", "analyze_single", tokens_used=50)
        log_file = tmp_path / "usage_log.jsonl"
        assert log_file.exists()

    def test_log_appends_records(self, tmp_path):
        svc = _service("pro", tmp_path)
        svc.log_usage("BTC/USDT", "1h", "analyze_single", tokens_used=50)
        svc.log_usage("ETH/USDT", "4h", "all_timeframes", tokens_used=120)
        log_file = tmp_path / "usage_log.jsonl"
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_log_record_fields(self, tmp_path):
        svc = _service("pro", tmp_path)
        svc.log_usage("SOL/USDT", "15m", "export_csv", tokens_used=30)
        log_file = tmp_path / "usage_log.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert record["symbol"] == "SOL/USDT"
        assert record["timeframe"] == "15m"
        assert record["feature"] == "export_csv"
        assert record["tokens_used"] == 30
        assert record["tier"] == "pro"
        assert "ts" in record

    def test_log_extra_fields(self, tmp_path):
        svc = _service("enterprise", tmp_path)
        svc.log_usage("BTC/USDT", "1d", "v6_scanner", tokens_used=0, extra={"pairs": 100})
        log_file = tmp_path / "usage_log.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert record["pairs"] == 100

    def test_log_creates_parent_dirs(self, tmp_path):
        nested_log = tmp_path / "deep" / "nested" / "usage.jsonl"
        svc = MonetizationService(tier=MonetizationTier.FREE, usage_log_path=nested_log)
        svc.log_usage("BTC/USDT", "1h", "analyze_single")
        assert nested_log.exists()

    def test_log_zero_tokens_default(self, tmp_path):
        svc = _service("free", tmp_path)
        svc.log_usage("BTC/USDT", "1h", "analyze_single")
        log_file = tmp_path / "usage_log.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert record["tokens_used"] == 0


# ---------------------------------------------------------------------------
# Usage report
# ---------------------------------------------------------------------------

class TestUsageReport:
    def _populate(self, svc: MonetizationService, records: list) -> None:
        for rec in records:
            svc.log_usage(**rec)

    def test_empty_log_returns_zeros(self, tmp_path):
        svc = _service("pro", tmp_path)
        report = svc.usage_report(days=30)
        assert report["total_calls"] == 0
        assert report["total_tokens_used"] == 0
        assert report["by_tier"] == {}

    def test_aggregation_counts(self, tmp_path):
        svc = _service("pro", tmp_path)
        self._populate(svc, [
            {"symbol": "BTC/USDT", "timeframe": "1h", "feature": "analyze_single", "tokens_used": 10},
            {"symbol": "BTC/USDT", "timeframe": "4h", "feature": "all_timeframes", "tokens_used": 20},
            {"symbol": "ETH/USDT", "timeframe": "1h", "feature": "analyze_single", "tokens_used": 15},
        ])
        report = svc.usage_report(days=30)
        assert report["total_calls"] == 3
        assert report["total_tokens_used"] == 45
        assert report["by_feature"]["analyze_single"] == 2
        assert report["by_feature"]["all_timeframes"] == 1
        assert report["by_symbol"]["BTC/USDT"] == 2
        assert report["by_symbol"]["ETH/USDT"] == 1
        assert report["by_tier"]["pro"] == 3

    def test_report_days_field(self, tmp_path):
        svc = _service("free", tmp_path)
        report = svc.usage_report(days=7)
        assert report["report_days"] == 7

    def test_log_path_in_report(self, tmp_path):
        svc = _service("free", tmp_path)
        report = svc.usage_report()
        assert "usage_log.jsonl" in report["log_path"]

    def test_mixed_tier_report(self, tmp_path):
        log_file = tmp_path / "usage_log.jsonl"
        # Write records manually with different tiers
        records = [
            {"ts": "2026-09-04T00:00:00+00:00", "tier": "free", "symbol": "BTC/USDT", "timeframe": "1h", "feature": "analyze_single", "tokens_used": 5},
            {"ts": "2026-09-04T01:00:00+00:00", "tier": "pro", "symbol": "ETH/USDT", "timeframe": "4h", "feature": "export_csv", "tokens_used": 20},
            {"ts": "2026-09-04T02:00:00+00:00", "tier": "enterprise", "symbol": "SOL/USDT", "timeframe": "1d", "feature": "v6_scanner", "tokens_used": 100},
        ]
        with open(log_file, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        svc = MonetizationService(tier=MonetizationTier.ENTERPRISE, usage_log_path=log_file)
        report = svc.usage_report(days=30)
        assert report["by_tier"]["free"] == 1
        assert report["by_tier"]["pro"] == 1
        assert report["by_tier"]["enterprise"] == 1
        assert report["total_tokens_used"] == 125


# ---------------------------------------------------------------------------
# Revenue estimate
# ---------------------------------------------------------------------------

class TestRevenueEstimate:
    def test_empty_log_zero_revenue(self, tmp_path):
        svc = _service("enterprise", tmp_path)
        rev = svc.revenue_estimate()
        assert rev["estimated_total_mrr_usd"] == 0.0
        assert rev["estimated_pro_seats"] == 0
        assert rev["estimated_enterprise_seats"] == 0

    def test_pro_calls_produce_revenue(self, tmp_path):
        log_file = tmp_path / "usage_log.jsonl"
        records = [
            {"ts": "2026-09-04T00:00:00+00:00", "tier": "pro", "symbol": "BTC/USDT", "timeframe": "1h", "feature": "analyze_single", "tokens_used": 0}
        ] * 150  # 150 pro calls → 1 seat estimate
        with open(log_file, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        svc = MonetizationService(tier=MonetizationTier.ENTERPRISE, usage_log_path=log_file)
        rev = svc.revenue_estimate(pro_price_usd=29.0)
        assert rev["pro_calls"] == 150
        assert rev["estimated_pro_seats"] >= 1
        assert rev["estimated_pro_mrr_usd"] >= 29.0

    def test_enterprise_calls_produce_revenue(self, tmp_path):
        log_file = tmp_path / "usage_log.jsonl"
        records = [
            {"ts": "2026-09-04T00:00:00+00:00", "tier": "enterprise", "symbol": "BTC/USDT", "timeframe": "1h", "feature": "v6_scanner", "tokens_used": 0}
        ] * 300  # 300 → 3 seats at $299
        with open(log_file, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        svc = MonetizationService(tier=MonetizationTier.ENTERPRISE, usage_log_path=log_file)
        rev = svc.revenue_estimate(enterprise_price_usd=299.0)
        assert rev["estimated_enterprise_seats"] == 3
        assert rev["estimated_enterprise_mrr_usd"] == 3 * 299.0

    def test_arr_is_12x_mrr(self, tmp_path):
        log_file = tmp_path / "usage_log.jsonl"
        records = [
            {"ts": "2026-09-04T00:00:00+00:00", "tier": "pro", "symbol": "BTC/USDT", "timeframe": "1h", "feature": "analyze_single", "tokens_used": 0}
        ] * 100
        with open(log_file, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        svc = MonetizationService(tier=MonetizationTier.ENTERPRISE, usage_log_path=log_file)
        rev = svc.revenue_estimate(pro_price_usd=29.0)
        assert rev["estimated_arr_usd"] == pytest.approx(rev["estimated_total_mrr_usd"] * 12)

    def test_revenue_note_is_present(self, tmp_path):
        svc = _service("enterprise", tmp_path)
        rev = svc.revenue_estimate()
        assert "note" in rev
        assert len(rev["note"]) > 10

    def test_price_params_used(self, tmp_path):
        log_file = tmp_path / "usage_log.jsonl"
        records = [
            {"ts": "2026-09-04T00:00:00+00:00", "tier": "pro", "symbol": "X", "timeframe": "1h", "feature": "analyze_single", "tokens_used": 0}
        ] * 100
        with open(log_file, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        svc = MonetizationService(tier=MonetizationTier.ENTERPRISE, usage_log_path=log_file)
        rev = svc.revenue_estimate(pro_price_usd=99.0)
        assert rev["pro_price_usd"] == 99.0
        assert rev["estimated_pro_mrr_usd"] == pytest.approx(99.0)  # 1 seat × $99


# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_has_required_keys(self, tmp_path):
        svc = _service("pro", tmp_path)
        s = svc.status()
        assert "current_tier" in s
        assert "available_features" in s
        assert "locked_features" in s
        assert "env_var" in s

    def test_status_current_tier_value(self, tmp_path):
        svc = _service("enterprise", tmp_path)
        assert svc.status()["current_tier"] == "enterprise"

    def test_status_all_tiers_listed(self, tmp_path):
        svc = _service("free", tmp_path)
        assert set(svc.status()["all_tiers"]) == {"free", "pro", "enterprise"}

    def test_monetize_status_module_function(self, monkeypatch, tmp_path):
        monkeypatch.setenv("EW_TIER", "free")
        # Reset singleton so env change takes effect
        import engine.monetize as m
        m._service = None
        s = monetize_status()
        assert s["current_tier"] == "free"
        m._service = None  # clean up
