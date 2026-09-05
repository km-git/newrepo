"""Tests for the Monetization Strategy Services broker layer."""

from __future__ import annotations

from datetime import datetime, timezone

from engine.monetize import (
  AccessDecision,
  LicenseTag,
  MonetizationBroker,
  RateCard,
  UsageEvent,
  run_monetize_demo,
)


def _now(y=2026, m=1, d=1):
  return datetime(y, m, d, tzinfo=timezone.utc)


def _proprietary_tag(**overrides):
  base = dict(
    asset_id="tape-001",
    license_id="LIC-1",
    license_type="proprietary",
    holder="Acme",
    usage_rights=["read", "train"],
    allow_list=["research-team"],
  )
  base.update(overrides)
  return LicenseTag(**base)


def test_license_tag_round_trip():
  tag = _proprietary_tag(expires_at="2027-01-01T00:00:00+00:00")
  restored = LicenseTag.from_dict(tag.to_dict())
  assert restored == tag


def test_tag_and_get_license():
  broker = MonetizationBroker()
  broker.tag_asset(_proprietary_tag())
  assert broker.get_license("tape-001").holder == "Acme"
  assert broker.get_license("missing") is None


def test_access_allow_when_action_in_rights():
  broker = MonetizationBroker()
  broker.tag_asset(_proprietary_tag())
  d = broker.check_access("research-team", "read", "tape-001", now=_now())
  assert isinstance(d, AccessDecision)
  assert d.allowed is True


def test_access_deny_when_action_not_permitted():
  broker = MonetizationBroker()
  # redistribute not in usage_rights, but principal is allow-listed
  broker.tag_asset(_proprietary_tag())
  d = broker.check_access("research-team", "redistribute", "tape-001", now=_now())
  assert d.allowed is False
  assert "usage_rights" in d.reason


def test_access_deny_on_expired_license():
  broker = MonetizationBroker()
  broker.tag_asset(_proprietary_tag(expires_at="2026-06-01T00:00:00+00:00"))
  # inject a "now" past expiry
  d = broker.check_access("research-team", "read", "tape-001", now=_now(2026, 7, 1))
  assert d.allowed is False
  assert "expired" in d.reason
  # before expiry the same access is allowed
  ok = broker.check_access("research-team", "read", "tape-001", now=_now(2026, 5, 1))
  assert ok.allowed is True


def test_public_domain_allows_all_actions():
  broker = MonetizationBroker()
  broker.tag_asset(LicenseTag(
    asset_id="pd-1",
    license_id="LIC-PD",
    license_type="public-domain",
    holder="PublicTrust",
    usage_rights=["read"],
    expires_at="2000-01-01T00:00:00+00:00",
  ))
  # even an unlisted action on an "expired" public-domain asset is allowed
  d = broker.check_access("anyone", "redistribute", "pd-1", now=_now())
  assert d.allowed is True
  assert "public-domain" in d.reason


def test_restricted_allow_list_enforcement():
  broker = MonetizationBroker()
  broker.tag_asset(LicenseTag(
    asset_id="r-1",
    license_id="LIC-R",
    license_type="restricted",
    holder="Gov",
    usage_rights=["read", "train"],
    allow_list=["alice"],
  ))
  allowed = broker.check_access("alice", "read", "r-1", now=_now())
  denied = broker.check_access("bob", "read", "r-1", now=_now())
  assert allowed.allowed is True
  assert denied.allowed is False
  assert "allow-list" in denied.reason


def test_check_access_untagged_asset_denies():
  broker = MonetizationBroker()
  d = broker.check_access("alice", "read", "ghost", now=_now())
  assert d.allowed is False
  assert "no license tag" in d.reason


def test_rate_card_per_access_fee():
  card = RateCard(per_access=0.25)
  ev = UsageEvent(asset_id="a", principal="p", action="read", gb=10.0, revenue=100.0)
  assert card.royalty_for(ev) == 0.25


def test_rate_card_per_gb_fee():
  card = RateCard(per_gb=0.10)
  ev = UsageEvent(asset_id="a", principal="p", action="read", gb=8.0)
  assert card.royalty_for(ev) == 0.8


def test_rate_card_revenue_share():
  card = RateCard(revenue_share_pct=15.0)
  ev = UsageEvent(asset_id="a", principal="p", action="read", revenue=200.0)
  assert card.royalty_for(ev) == 30.0


def test_rate_card_resolution_precedence():
  broker = MonetizationBroker(
    default_rate_card=RateCard(per_access=0.01),
    rate_cards_by_type={"proprietary": RateCard(per_access=1.0)},
    rate_cards_by_holder={"Acme": RateCard(per_access=5.0)},
  )
  tag = _proprietary_tag(holder="Acme")
  assert broker.rate_card_for(tag).per_access == 5.0
  # falls back to type when holder has no card
  tag2 = _proprietary_tag(holder="Other")
  assert broker.rate_card_for(tag2).per_access == 1.0
  # falls back to default when neither matches
  assert broker.rate_card_for(None).per_access == 0.01


def test_royalty_report_aggregates_multiple_holders():
  broker = MonetizationBroker(
    default_rate_card=RateCard(per_access=1.0, per_gb=0.5, revenue_share_pct=10.0),
  )
  broker.tag_asset(_proprietary_tag(asset_id="a1", holder="Acme"))
  broker.tag_asset(_proprietary_tag(asset_id="b1", holder="Beta"))
  broker.record_usage("a1", "p", "read", gb=2.0, revenue=100.0)  # 1 + 1 + 10 = 12
  broker.record_usage("a1", "p", "train", gb=0.0, revenue=0.0)   # 1
  broker.record_usage("b1", "q", "read", gb=4.0)                 # 1 + 2 = 3

  report = broker.royalty_report()
  assert report["event_count"] == 3
  assert report["grand_total_fees"] == 16.0
  holders = {h["holder"]: h for h in report["holders"]}
  assert holders["Acme"]["total_fees"] == 13.0
  assert holders["Acme"]["event_count"] == 2
  assert holders["Beta"]["total_fees"] == 3.0
  # per-asset breakdown present
  assert holders["Acme"]["assets"][0]["asset_id"] == "a1"
  # holders sorted by total fees desc
  assert report["holders"][0]["holder"] == "Acme"


def test_royalty_report_unlicensed_asset_bucket():
  broker = MonetizationBroker(default_rate_card=RateCard(per_access=2.0))
  broker.record_usage("untagged", "p", "read")
  report = broker.royalty_report()
  holders = {h["holder"]: h for h in report["holders"]}
  assert "unlicensed" in holders
  assert holders["unlicensed"]["total_fees"] == 2.0


def test_json_persistence_round_trip_env(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_MONETIZE_STATE", str(tmp_path / "monetize.json"))
  broker = MonetizationBroker(
    default_rate_card=RateCard(per_access=1.0, per_gb=0.5),
    rate_cards_by_type={"proprietary": RateCard(per_access=2.0)},
  )
  broker.tag_asset(_proprietary_tag(expires_at="2027-01-01T00:00:00+00:00"))
  broker.record_usage("tape-001", "research-team", "train", gb=3.0, revenue=50.0)
  saved = broker.save()
  assert saved.exists()

  restored = MonetizationBroker.load()
  assert restored.get_license("tape-001") == broker.get_license("tape-001")
  assert len(restored.events) == 1
  assert restored.default_rate_card == broker.default_rate_card
  assert restored.rate_cards_by_type["proprietary"].per_access == 2.0
  # reports match after round-trip
  assert restored.royalty_report()["grand_total_fees"] == broker.royalty_report()["grand_total_fees"]


def test_json_persistence_explicit_path(tmp_path):
  path = tmp_path / "manifest.json"
  broker = MonetizationBroker()
  broker.tag_asset(_proprietary_tag())
  broker.save(path)
  restored = MonetizationBroker.load(path)
  assert restored.get_license("tape-001") == broker.get_license("tape-001")


def test_load_missing_returns_empty(tmp_path):
  restored = MonetizationBroker.load(tmp_path / "nope.json")
  assert restored.tags == {}
  assert restored.events == []


def test_run_monetize_demo():
  report = run_monetize_demo()
  assert report["access_allowed"]["allowed"] is True
  assert report["access_denied"]["allowed"] is False
  assert report["royalty_report"]["event_count"] == 2
  # proprietary rate card applied to AcmeArchives usage
  holders = {h["holder"]: h for h in report["royalty_report"]["holders"]}
  assert "AcmeArchives" in holders
