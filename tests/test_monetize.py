"""Tests for Monetization Strategy Services broker."""

from __future__ import annotations

import json

from engine.monetize import (
  LICENSE_ADVISORY,
  LICENSE_COMMERCIAL,
  LICENSE_INTERNAL,
  LICENSE_PAPER,
  LICENSE_RESEARCH,
  VERDICT_BUILD,
  VERDICT_CUT,
  VERDICT_HOLD,
  check_access,
  classify_bet,
  friday_review,
  idea_score,
  license_catalog,
  load_ledger,
  monetize_enabled,
  parse_discovery_ideas,
  recommend_bets,
  record_usage,
  royalty_rate,
  royalty_report,
  run_monetize_report,
  tag_license,
)


SAMPLE_DISCOVERY = """
### Rank 2 — SWMS Studio
- **Category:** Tradie / NDIS
- **Build days:** 14
- **Pricing AUD:** $49–99/month
- **Conservative Y1 midpoint revenue AUD:** $18,000
- **Validation probability:** ~50% (estimate)
- **First-customer route:** Existing builder clients
- **Risk:** WHS advice line

### Rank 9 — ReviewReply Desk
- **Category:** AI Tools SMB
- **Build days:** 10
- **Pricing AUD:** $49–99/month per location
- **Conservative Y1 midpoint revenue AUD:** $14,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Existing IT-services clients with storefronts
- **Risk:** Platform API policy changes

### Rank 41 — PolicyPack Drafter (NDIS)
- **Category:** AI Compliance
- **Build days:** 14
- **Conservative Y1 midpoint revenue AUD:** $9,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** NDIS provider startup groups
- **Risk:** Advice line

### Rank 49 — WeakBet
- **Category:** AI Tools SMB
- **Build days:** 12
- **Conservative Y1 midpoint revenue AUD:** $1,000
- **Validation probability:** ~20% (estimate)
- **First-customer route:**
- **Risk:** Unproven
"""


def test_monetize_enabled_default():
  assert monetize_enabled() is True


def test_license_catalog_has_five_policies():
  catalog = license_catalog()
  ids = {row["id"] for row in catalog}
  assert ids == {
    LICENSE_RESEARCH,
    LICENSE_PAPER,
    LICENSE_INTERNAL,
    LICENSE_ADVISORY,
    LICENSE_COMMERCIAL,
  }
  assert royalty_rate(LICENSE_COMMERCIAL) == 0.15
  assert royalty_rate(LICENSE_ADVISORY) == 0.05
  assert royalty_rate(LICENSE_RESEARCH) == 0.0


def test_tag_setup_defaults_to_research():
  tagged = tag_license({"symbol": "BTC/USDT", "kind": "setup"})
  assert tagged["license_id"] == LICENSE_RESEARCH
  assert tagged["kind"] == "setup"
  assert tagged["artifact_id"] == "BTC/USDT"


def test_tag_setup_paper_and_internal():
  paper = tag_license({"id": "s1", "gtc_tier": "monitor", "honest_execution_tier": "probe"})
  assert paper["license_id"] == LICENSE_PAPER
  internal = tag_license(
    {"id": "s2", "gtc_tier": "executable", "executive_verdict": "GO"}
  )
  assert internal["license_id"] == LICENSE_INTERNAL


def test_tag_idea_compliance_stays_research():
  tagged = tag_license(
    {
      "kind": "idea",
      "name": "PolicyPack",
      "category": "AI Compliance",
      "verdict": VERDICT_BUILD,
    }
  )
  assert tagged["license_id"] == LICENSE_RESEARCH


def test_access_research_forbids_export_and_live():
  view = check_access("operator", "view", LICENSE_RESEARCH)
  assert view["allow"] is True
  export = check_access("operator", "export", LICENSE_RESEARCH)
  assert export["allow"] is False
  live = check_access("operator", "live_exec", LICENSE_INTERNAL, confirm_live=False)
  assert live["allow"] is False
  assert "EW_EXECUTE_CONFIRM" in live["reason"]


def test_access_live_with_confirm():
  ok = check_access("operator", "live_exec", LICENSE_INTERNAL, confirm_live=True)
  assert ok["allow"] is True
  denied = check_access("operator", "third_party_license", LICENSE_INTERNAL, confirm_live=True)
  assert denied["allow"] is False


def test_third_party_requires_commercial():
  denied = check_access("third_party", "view", LICENSE_ADVISORY)
  assert denied["allow"] is False
  ok = check_access("third_party", "third_party_license", LICENSE_COMMERCIAL, confirm_live=True)
  assert ok["allow"] is True


def test_unknown_action_denied():
  decision = check_access("operator", "delete_ledger", LICENSE_COMMERCIAL)
  assert decision["allow"] is False
  assert decision["reason"].startswith("unknown_action")


def test_record_usage_and_royalty_report(tmp_path):
  ledger = tmp_path / "ledger.json"
  ev = record_usage(
    "ReviewReply Desk",
    "export",
    license_id=LICENSE_COMMERCIAL,
    notional=1000.0,
    path=ledger,
  )
  assert ev["royalty_due"] == 150.0
  record_usage(
    "ReviewReply Desk",
    "view",
    license_id=LICENSE_RESEARCH,
    notional=100.0,
    path=ledger,
  )
  report = royalty_report(path=ledger)
  assert report["event_count"] == 2
  assert report["total_royalty_due"] == 150.0
  assert report["by_license"][LICENSE_COMMERCIAL]["royalty_due"] == 150.0
  stored = load_ledger(ledger)
  assert len(stored["events"]) == 2


def test_negative_notional_clamped(tmp_path):
  ledger = tmp_path / "ledger.json"
  ev = record_usage("x", "view", license_id=LICENSE_COMMERCIAL, notional=-50, path=ledger)
  assert ev["notional"] == 0.0
  assert ev["royalty_due"] == 0.0


def test_parse_discovery_ideas():
  ideas = parse_discovery_ideas(SAMPLE_DISCOVERY)
  assert len(ideas) == 4
  review = next(i for i in ideas if i["name"] == "ReviewReply Desk")
  assert review["rank"] == 9
  assert review["y1_revenue"] == 14000.0
  assert review["validation_prob"] == 0.45
  assert review["build_days"] == 10
  assert "storefronts" in review["first_customer_route"]


def test_idea_score_and_classify():
  strong = {
    "validation_prob": 0.45,
    "y1_revenue": 14000.0,
    "build_days": 10,
    "first_customer_route": "Existing clients",
  }
  assert idea_score(strong) == 630.0
  assert classify_bet(strong) == VERDICT_BUILD
  weak = {
    "validation_prob": 0.20,
    "y1_revenue": 1000.0,
    "build_days": 12,
    "first_customer_route": "",
  }
  assert classify_bet(weak) == VERDICT_CUT
  mid = {
    "validation_prob": 0.30,
    "y1_revenue": 4000.0,
    "build_days": 10,
    "first_customer_route": "Chamber",
  }
  assert classify_bet(mid) == VERDICT_HOLD


def test_recommend_bets_and_friday_review():
  ideas = parse_discovery_ideas(SAMPLE_DISCOVERY)
  ranked = recommend_bets(ideas)
  by_name = {r["name"]: r for r in ranked}
  assert by_name["ReviewReply Desk"]["verdict"] == VERDICT_BUILD
  assert by_name["ReviewReply Desk"]["license_id"] == LICENSE_COMMERCIAL
  assert by_name["PolicyPack Drafter (NDIS)"]["verdict"] == VERDICT_BUILD
  assert by_name["PolicyPack Drafter (NDIS)"]["license_id"] == LICENSE_RESEARCH
  assert by_name["WeakBet"]["verdict"] == VERDICT_CUT
  review = friday_review(ideas)
  assert review["idea_count"] == 4
  assert review["by_verdict"][VERDICT_CUT] == 1
  assert review["by_verdict"][VERDICT_BUILD] >= 2
  assert any(x["name"] == "ReviewReply Desk" for x in review["top_builds"])


def test_build_cap_demotes_overflow():
  ideas = []
  for i in range(60):
    ideas.append(
      {
        "name": f"Bet {i}",
        "rank": i,
        "validation_prob": 0.50,
        "y1_revenue": 20000.0 - i,
        "build_days": 10,
        "first_customer_route": "Existing book",
        "category": "AI Tools SMB",
      }
    )
  ranked = recommend_bets(ideas)
  builds = [r for r in ranked if r["verdict"] == VERDICT_BUILD]
  holds = [r for r in ranked if r["verdict"] == VERDICT_HOLD]
  cuts = [r for r in ranked if r["verdict"] == VERDICT_CUT]
  assert len(builds) == 55
  assert len(holds) == 0
  assert len(cuts) == 5
  assert all(c.get("cap_reason") for c in cuts)
  review = friday_review(ideas)
  assert review["active_bets"] == 55
  assert review["within_bet_band"] is True


def test_run_monetize_report_persists(tmp_path, monkeypatch):
  import engine.monetize as mz

  discovery = tmp_path / "discovery-output.md"
  discovery.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
  report_path = tmp_path / "report.json"
  ledger = tmp_path / "ledger.json"
  monkeypatch.setattr(mz, "REPORT_PATH", report_path)
  monkeypatch.setattr(mz, "LEDGER_PATH", ledger)
  monkeypatch.setattr(mz, "DISCOVERY_PATH", discovery)
  result = mz.run_monetize_report(
    persist=True,
    discovery_path=discovery,
    ledger_path=ledger,
    artifacts=[{"id": "BTC/USDT", "gtc_tier": "watch"}],
  )
  assert not result.get("skipped")
  assert result["module"] == "monetize"
  assert result["money_movement"] is False
  assert result["discovery_ideas"] == 4
  assert result["tagged_setups"][0]["license_id"] == LICENSE_PAPER
  assert report_path.exists()
  saved = json.loads(report_path.read_text(encoding="utf-8"))
  assert saved["label"] == "Monetization Strategy Services"


def test_run_monetize_disabled(monkeypatch):
  import engine.monetize as mz

  monkeypatch.setenv("EW_MONETIZE", "0")
  result = mz.run_monetize_report(persist=False)
  assert result.get("skipped") is True


def test_parse_real_discovery_file():
  from pathlib import Path

  path = Path("discovery-output.md")
  if not path.exists():
    return
  ideas = parse_discovery_ideas(path.read_text(encoding="utf-8"))
  assert len(ideas) >= 40
  names = {i["name"] for i in ideas}
  assert "ReviewReply Desk" in names
  assert all("rank" in i and "name" in i for i in ideas)
  review = friday_review(ideas)
  assert review["idea_count"] == len(ideas)
  assert review["active_bets"] <= 55
  assert review["within_bet_band"] is True
