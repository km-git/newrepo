"""Unit tests for engine.monetize — LicenseTagger, AccessController, RoyaltyReporter.

All tests are offline-safe (no network calls, no live data).
"""

from __future__ import annotations

import json
import os

import pytest

from engine.monetize import (
    FEATURE_DESCRIPTIONS,
    TIERS,
    AccessController,
    LicenseTagger,
    RoyaltyReporter,
    features_for_tier,
    monetize_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(**kwargs) -> dict:
    return {"symbol": "BTC/USDT", "status": "ok", **kwargs}


# ---------------------------------------------------------------------------
# LicenseTagger
# ---------------------------------------------------------------------------


class TestLicenseTagger:
    def test_tag_adds_license_block(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="free")
        assert "_license" in payload

    def test_tag_returns_same_dict(self):
        payload = _make_payload()
        returned = LicenseTagger.tag(payload, tier="free")
        assert returned is payload

    def test_tag_free_tier_fields(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="free")
        block = payload["_license"]
        assert block["tier"] == "free"
        assert "single_symbol" in block["features"]
        assert "tagged_at" in block

    def test_tag_pro_includes_batch(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="pro")
        assert "batch" in payload["_license"]["features"]

    def test_tag_enterprise_includes_live_execution(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="enterprise")
        assert "live_execution" in payload["_license"]["features"]

    def test_tag_extra_merged(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="free", extra={"customer_id": "cust_123"})
        assert payload["_license"]["customer_id"] == "cust_123"

    def test_strip_removes_license(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="free")
        LicenseTagger.strip(payload)
        assert "_license" not in payload

    def test_strip_no_error_when_absent(self):
        payload = _make_payload()
        LicenseTagger.strip(payload)  # should not raise
        assert "_license" not in payload

    def test_read_returns_block(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="pro")
        block = LicenseTagger.read(payload)
        assert block is not None
        assert block["tier"] == "pro"

    def test_read_returns_none_when_absent(self):
        payload = _make_payload()
        assert LicenseTagger.read(payload) is None

    def test_tag_uses_env_var(self, monkeypatch):
        monkeypatch.setenv("EW_LICENSE_TIER", "pro")
        payload = _make_payload()
        LicenseTagger.tag(payload)
        assert payload["_license"]["tier"] == "pro"

    def test_tag_invalid_tier_defaults_to_free(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="invalid_tier_xyz")
        assert payload["_license"]["tier"] == "free"

    def test_features_list_is_sorted(self):
        payload = _make_payload()
        LicenseTagger.tag(payload, tier="enterprise")
        features = payload["_license"]["features"]
        assert features == sorted(features)


# ---------------------------------------------------------------------------
# AccessController
# ---------------------------------------------------------------------------


class TestAccessController:
    def test_free_tier_default(self, monkeypatch):
        monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
        ac = AccessController()
        assert ac.tier == "free"

    def test_env_var_sets_tier(self, monkeypatch):
        monkeypatch.setenv("EW_LICENSE_TIER", "enterprise")
        ac = AccessController()
        assert ac.tier == "enterprise"

    def test_explicit_tier_overrides_env(self, monkeypatch):
        monkeypatch.setenv("EW_LICENSE_TIER", "enterprise")
        ac = AccessController(tier="pro")
        assert ac.tier == "pro"

    def test_invalid_tier_falls_back_to_free(self):
        ac = AccessController(tier="gold")
        assert ac.tier == "free"

    # can()
    def test_free_can_single_symbol(self):
        assert AccessController(tier="free").can("single_symbol") is True

    def test_free_cannot_batch(self):
        assert AccessController(tier="free").can("batch") is False

    def test_free_cannot_live_execution(self):
        assert AccessController(tier="free").can("live_execution") is False

    def test_pro_can_batch(self):
        assert AccessController(tier="pro").can("batch") is True

    def test_pro_can_brain_okf(self):
        assert AccessController(tier="pro").can("brain_okf") is True

    def test_pro_cannot_live_execution(self):
        assert AccessController(tier="pro").can("live_execution") is False

    def test_enterprise_can_live_execution(self):
        assert AccessController(tier="enterprise").can("live_execution") is True

    def test_enterprise_can_v6_scanner(self):
        assert AccessController(tier="enterprise").can("v6_scanner") is True

    def test_enterprise_can_all_features(self):
        ac = AccessController(tier="enterprise")
        for feature in features_for_tier("enterprise"):
            assert ac.can(feature), f"enterprise should have {feature}"

    # require()
    def test_require_passes_when_allowed(self):
        ac = AccessController(tier="pro")
        ac.require("batch")  # should not raise

    def test_require_raises_when_denied(self):
        ac = AccessController(tier="free")
        with pytest.raises(AccessController.AccessDeniedError):
            ac.require("batch")

    def test_access_denied_is_permission_error(self):
        ac = AccessController(tier="free")
        with pytest.raises(PermissionError):
            ac.require("live_execution")

    def test_error_message_mentions_feature(self):
        ac = AccessController(tier="free")
        with pytest.raises(AccessController.AccessDeniedError, match="batch"):
            ac.require("batch")

    def test_error_message_mentions_required_tier(self):
        ac = AccessController(tier="free")
        with pytest.raises(AccessController.AccessDeniedError, match="pro"):
            ac.require("batch")

    # denied_features()
    def test_free_has_denied_features(self):
        ac = AccessController(tier="free")
        denied = ac.denied_features()
        assert "batch" in denied
        assert "live_execution" in denied

    def test_enterprise_has_no_denied_features(self):
        ac = AccessController(tier="enterprise")
        assert ac.denied_features() == []

    def test_denied_features_sorted(self):
        ac = AccessController(tier="free")
        denied = ac.denied_features()
        assert denied == sorted(denied)

    # access_matrix()
    def test_access_matrix_keys(self):
        ac = AccessController(tier="pro")
        matrix = ac.access_matrix()
        assert "tier" in matrix
        assert "allowed" in matrix
        assert "denied" in matrix
        assert "descriptions" in matrix

    def test_access_matrix_tier_matches(self):
        ac = AccessController(tier="pro")
        assert ac.access_matrix()["tier"] == "pro"

    def test_access_matrix_descriptions_cover_enterprise(self):
        ac = AccessController(tier="enterprise")
        matrix = ac.access_matrix()
        for feat in features_for_tier("enterprise"):
            assert feat in matrix["descriptions"]

    def test_access_matrix_serialisable(self):
        ac = AccessController(tier="free")
        json.dumps(ac.access_matrix())  # must not raise


# ---------------------------------------------------------------------------
# RoyaltyReporter
# ---------------------------------------------------------------------------


class TestRoyaltyReporter:
    def test_report_structure(self):
        rr = RoyaltyReporter(tier="free")
        report = rr.report()
        assert "tier" in report
        assert "generated_at" in report
        assert "usage" in report
        assert "detail" in report

    def test_initial_counters_zero(self):
        rr = RoyaltyReporter(tier="free")
        usage = rr.report()["usage"]
        assert usage["setups_generated"] == 0
        assert usage["signals_fired"] == 0
        assert usage["tickers_scanned"] == 0

    def test_record_setup_increments(self):
        rr = RoyaltyReporter(tier="free")
        rr.record_setup("BTC/USDT").record_setup("ETH/USDT")
        assert rr.report()["usage"]["setups_generated"] == 2

    def test_record_signal_increments(self):
        rr = RoyaltyReporter(tier="pro")
        rr.record_signal("BTC/USDT", "SHORT").record_signal("ETH/USDT", "LONG")
        assert rr.report()["usage"]["signals_fired"] == 2

    def test_record_ticker_increments(self):
        rr = RoyaltyReporter(tier="enterprise")
        rr.record_ticker("BTC/USDT").record_ticker("SOL/USDT")
        assert rr.report()["usage"]["tickers_scanned"] == 2

    def test_record_tickers_batch(self):
        rr = RoyaltyReporter()
        rr.record_tickers(["A", "B", "C"])
        assert rr.report()["usage"]["tickers_scanned"] == 3

    def test_record_setup_chaining(self):
        rr = RoyaltyReporter()
        returned = rr.record_setup("X")
        assert returned is rr  # fluent interface

    def test_detail_includes_symbols(self):
        rr = RoyaltyReporter()
        rr.record_setup("BTC/USDT")
        assert "BTC/USDT" in rr.report()["detail"]["setups"]

    def test_detail_signals_have_direction(self):
        rr = RoyaltyReporter()
        rr.record_signal("BTC/USDT", "LONG")
        signals = rr.report()["detail"]["signals"]
        assert any(s["direction"] == "LONG" for s in signals)

    def test_report_tier_matches(self):
        rr = RoyaltyReporter(tier="enterprise")
        assert rr.report()["tier"] == "enterprise"

    def test_report_serialisable(self):
        rr = RoyaltyReporter()
        rr.record_setup("BTC/USDT").record_signal("BTC/USDT")
        json.dumps(rr.report())  # must not raise

    # save / load
    def test_save_creates_file(self, tmp_path):
        rr = RoyaltyReporter(report_path=tmp_path / "royalty.json")
        rr.record_setup("BTC/USDT")
        path = rr.save(merge=False)
        assert path.exists()

    def test_save_content_valid_json(self, tmp_path):
        rr = RoyaltyReporter(report_path=tmp_path / "royalty.json")
        rr.record_setup("ETH/USDT")
        path = rr.save(merge=False)
        data = json.loads(path.read_text())
        assert data["usage"]["setups_generated"] == 1

    def test_save_merge_accumulates(self, tmp_path):
        p = tmp_path / "royalty.json"
        rr1 = RoyaltyReporter(report_path=p)
        rr1.record_setup("BTC/USDT")
        rr1.save(merge=False)

        rr2 = RoyaltyReporter(report_path=p)
        rr2.record_setup("ETH/USDT")
        rr2.save(merge=True)

        data = json.loads(p.read_text())
        assert data["usage"]["setups_generated"] == 2

    def test_save_no_merge_overwrites(self, tmp_path):
        p = tmp_path / "royalty.json"
        rr1 = RoyaltyReporter(report_path=p)
        rr1.record_setup("BTC/USDT").record_setup("ETH/USDT")
        rr1.save(merge=False)

        rr2 = RoyaltyReporter(report_path=p)
        rr2.record_setup("SOL/USDT")
        rr2.save(merge=False)

        data = json.loads(p.read_text())
        assert data["usage"]["setups_generated"] == 1

    def test_load_returns_empty_when_no_file(self, tmp_path):
        result = RoyaltyReporter.load(report_path=tmp_path / "nonexistent.json")
        assert result == {}

    def test_load_returns_saved_report(self, tmp_path):
        p = tmp_path / "royalty.json"
        rr = RoyaltyReporter(report_path=p)
        rr.record_setup("BTC/USDT")
        rr.save(merge=False)
        loaded = RoyaltyReporter.load(report_path=p)
        assert loaded["usage"]["setups_generated"] == 1

    def test_save_creates_parent_dirs(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "royalty.json"
        rr = RoyaltyReporter(report_path=deep)
        rr.record_setup("X")
        rr.save(merge=False)
        assert deep.exists()

    def test_uses_env_var_for_tier(self, monkeypatch):
        monkeypatch.setenv("EW_LICENSE_TIER", "enterprise")
        rr = RoyaltyReporter()
        assert rr.report()["tier"] == "enterprise"


# ---------------------------------------------------------------------------
# features_for_tier helper
# ---------------------------------------------------------------------------


class TestFeaturesForTier:
    def test_free_features_subset_of_pro(self):
        free = features_for_tier("free")
        pro = features_for_tier("pro")
        assert free.issubset(pro)

    def test_pro_features_subset_of_enterprise(self):
        pro = features_for_tier("pro")
        ent = features_for_tier("enterprise")
        assert pro.issubset(ent)

    def test_all_tiers_valid(self):
        for t in TIERS:
            feats = features_for_tier(t)
            assert len(feats) > 0

    def test_invalid_tier_returns_free_features(self):
        free = features_for_tier("free")
        invalid = features_for_tier("nonexistent")
        assert free == invalid


# ---------------------------------------------------------------------------
# monetize_status helper
# ---------------------------------------------------------------------------


class TestMonetizeStatus:
    def test_status_keys(self):
        status = monetize_status(tier="free")
        assert "license" in status
        assert "royalty_report" in status

    def test_status_license_has_tier(self):
        status = monetize_status(tier="pro")
        assert status["license"]["tier"] == "pro"

    def test_status_serialisable(self):
        status = monetize_status(tier="enterprise")
        json.dumps(status)  # must not raise


# ---------------------------------------------------------------------------
# FEATURE_DESCRIPTIONS completeness
# ---------------------------------------------------------------------------


def test_feature_descriptions_cover_all_enterprise():
    all_feats = features_for_tier("enterprise")
    for feat in all_feats:
        assert feat in FEATURE_DESCRIPTIONS, f"Missing description for feature: {feat}"
