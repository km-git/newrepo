"""Tests for engine/monetize.py — signal licensing + royalty desk."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.monetize import (
  ALL_TIERS,
  REPORT_JSON,
  REPORT_MD,
  TIER_ENTERPRISE,
  TIER_FREE,
  TIER_PRO,
  TierPolicy,
  apply_license,
  build_report,
  default_tier_policies,
  get_policy,
  royalty_report,
  run_monetize_report,
  signal_hash,
  watermark_id,
  write_reports,
)


def _sig(**overrides) -> dict:
  base = {
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "direction": "LONG",
    "wae": 100.0,
    "stop_loss": 95.0,
    "tp1": 110.0,
    "tp2": 120.0,
    "tp3": 130.0,
    "tp1_exit_pct": 50,
    "gtc_tier": "executable",
    "honest_execution_tier": "full",
  }
  base.update(overrides)
  return base


def test_default_policies_shape():
  policies = default_tier_policies()
  assert set(policies) == set(ALL_TIERS)
  free = policies[TIER_FREE]
  pro = policies[TIER_PRO]
  ent = policies[TIER_ENTERPRISE]
  assert free.monthly_price_aud == 0.0
  assert pro.monthly_price_aud > 0
  assert ent.monthly_price_aud > pro.monthly_price_aud
  assert free.tf_allowlist == frozenset({"1d", "1w"})
  assert pro.tf_allowlist is None
  assert ent.royalty_pct_of_r > 0


def test_get_policy_unknown_raises():
  with pytest.raises(ValueError):
    get_policy("platinum")


def test_signal_hash_is_deterministic_and_ordering_independent():
  a = _sig(symbol="ETH/USDT", timeframe="4h", direction="SHORT")
  b = {"tp1": 110.0, "wae": 100.0, "symbol": "ETH/USDT", "timeframe": "4h",
       "direction": "SHORT", "stop_loss": 95.0, "tp2": 120.0, "tp3": 130.0,
       "gtc_tier": "executable", "honest_execution_tier": "full",
       "tp1_exit_pct": 50, "extra": "ignored"}
  a_hash = signal_hash(a)
  b_hash = signal_hash(b)
  assert a_hash == b_hash
  assert len(a_hash) == 64


def test_signal_hash_changes_when_price_changes():
  a = _sig()
  b = _sig(wae=101.0)
  assert signal_hash(a) != signal_hash(b)


def test_watermark_id_deterministic_and_tier_scoped():
  s = _sig()
  wm_pro_a = watermark_id(s, TIER_PRO)
  wm_pro_b = watermark_id(s, TIER_PRO)
  wm_free = watermark_id(s, TIER_FREE)
  assert wm_pro_a == wm_pro_b
  assert wm_pro_a.startswith("wm_pro_")
  assert wm_free.startswith("wm_free_")
  assert wm_pro_a != wm_free


def test_apply_license_filters_free_tier_by_tf():
  sigs = [_sig(timeframe="1h"), _sig(timeframe="1d"), _sig(timeframe="1w")]
  free = apply_license(sigs, TIER_FREE)
  tfs = sorted({row["timeframe"] for row in free})
  assert tfs == ["1d", "1w"]
  pro = apply_license(sigs, TIER_PRO)
  assert len(pro) == 3


def test_apply_license_free_tier_redacts_entry_sl_tp():
  sigs = [_sig(timeframe="1d")]
  free = apply_license(sigs, TIER_FREE)
  assert len(free) == 1
  row = free[0]
  # No exact prices leak
  for hidden in ("wae", "stop_loss", "tp1", "tp2", "tp3"):
    assert hidden not in row, f"free tier leaked {hidden}"
  # Delayed hint is a rough approximation, not the exact WAE
  assert "delayed_hint" in row
  assert row["delayed_hint"] == "~100"
  # License and royalty terms attached
  lic = row["license"]
  assert lic["tier"] == TIER_FREE
  assert lic["watermark_id"].startswith("wm_free_")
  assert lic["signal_hash"] == signal_hash(sigs[0])
  assert lic["redistribution_allowed"] is True
  assert lic["expiry_utc"] == "delayed_24h"
  assert row["royalty_terms"]["monthly_price_aud"] == 0.0


def test_apply_license_pro_tier_keeps_entry_sl_tp():
  sigs = [_sig(timeframe="4h")]
  pro = apply_license(sigs, TIER_PRO)
  assert len(pro) == 1
  row = pro[0]
  assert row["wae"] == 100.0
  assert row["stop_loss"] == 95.0
  assert row["tp1"] == 110.0
  assert row["license"]["tier"] == TIER_PRO
  assert row["license"]["expiry_utc"] is None
  assert row["license"]["redistribution_allowed"] is False


def test_apply_license_enterprise_adds_paper_and_custom_risk_terms():
  sigs = [_sig()]
  ent = apply_license(sigs, TIER_ENTERPRISE)
  assert len(ent) == 1
  terms = ent[0]["royalty_terms"]
  assert terms["paper_fill_included"] is True
  assert terms["custom_risk_profile"] is True
  assert terms["royalty_pct_of_r"] > 0


def test_apply_license_respects_max_signals_per_day():
  sigs = [_sig(timeframe="1d", symbol=f"SYM{i}/USDT") for i in range(10)]
  free = apply_license(sigs, TIER_FREE)
  assert len(free) == 3


def test_apply_license_ignores_non_dict_entries():
  sigs = [_sig(timeframe="1d"), None, "junk", 42, _sig(timeframe="1w")]
  free = apply_license(sigs, TIER_FREE)
  assert len(free) == 2


def test_apply_license_watermarks_stable_across_calls():
  s = _sig(timeframe="1d")
  a = apply_license([s], TIER_FREE)[0]["license"]["watermark_id"]
  b = apply_license([s], TIER_FREE)[0]["license"]["watermark_id"]
  assert a == b


def _out(status: str, **overrides) -> dict:
  base = _sig(status=status, license_tier=TIER_PRO)
  base.update(overrides)
  return base


def test_royalty_report_expected_revenue_and_royalty():
  # 3 wins + 1 loss on Pro, tp1_exit_pct=50 → per-win R = (10/5)*0.5 = 1.0
  outcomes = [
    _out("tp1_hit"),
    _out("tp1_hit"),
    _out("tp1_hit"),
    _out("sl_hit"),
    _out("expired"),
    _out("tp1_hit", license_tier=TIER_ENTERPRISE),
  ]
  subs = {TIER_FREE: 20, TIER_PRO: 4, TIER_ENTERPRISE: 2}
  report = royalty_report(outcomes, active_subscribers=subs, months=2)
  per_tier = report["per_tier"]

  # Subscription revenue = price × subs × months
  assert per_tier[TIER_FREE]["subscription_revenue_aud"] == 0.0
  assert per_tier[TIER_PRO]["subscription_revenue_aud"] == pytest.approx(49.0 * 4 * 2)
  assert per_tier[TIER_ENTERPRISE]["subscription_revenue_aud"] == pytest.approx(249.0 * 2 * 2)

  # Pro: 3 wins × 1R + 1 loss × -1R = 2R sum, 3R positive, royalty 0
  assert per_tier[TIER_PRO]["wins"] == 3
  assert per_tier[TIER_PRO]["losses"] == 1
  assert per_tier[TIER_PRO]["expired"] == 1
  assert per_tier[TIER_PRO]["sum_r"] == pytest.approx(2.0)
  assert per_tier[TIER_PRO]["positive_r"] == pytest.approx(3.0)
  assert per_tier[TIER_PRO]["royalty_r"] == 0.0
  assert per_tier[TIER_PRO]["win_rate"] == pytest.approx(0.75)

  # Enterprise: 1 win × 1R positive, royalty = 1R * 0.10 = 0.10
  assert per_tier[TIER_ENTERPRISE]["wins"] == 1
  assert per_tier[TIER_ENTERPRISE]["positive_r"] == pytest.approx(1.0)
  assert per_tier[TIER_ENTERPRISE]["royalty_r"] == pytest.approx(0.10)

  totals = report["totals"]
  assert totals["subscribers"] == 26
  # 49*4*2 + 249*2*2 = 392 + 996 = 1388
  assert totals["subscription_revenue_aud"] == pytest.approx(1388.0)
  assert totals["royalty_revenue_aud"] == pytest.approx(0.10)


def test_royalty_report_counts_invalid_outcomes():
  outcomes = [_out("tp1_hit"), {"license_tier": "pro"}, "junk", {"status": "tp1_hit", "license_tier": "platinum"}]
  report = royalty_report(outcomes, active_subscribers={TIER_PRO: 0})
  assert report["invalid_outcomes"] >= 2
  assert report["per_tier"][TIER_PRO]["wins"] == 1


def test_royalty_report_watermark_reconciliation():
  s1 = _sig(symbol="AAA/USDT", timeframe="1h")
  s2 = _sig(symbol="BBB/USDT", timeframe="1h")
  outcomes = [
    dict(s1, status="tp1_hit", license_tier=TIER_PRO, watermark_id=watermark_id(s1, TIER_PRO)),
    dict(s2, status="sl_hit", license_tier=TIER_PRO, watermark_id=watermark_id(s2, TIER_PRO)),
    dict(s1, status="tp1_hit", license_tier=TIER_PRO, watermark_id=watermark_id(s1, TIER_PRO)),
  ]
  report = royalty_report(outcomes, active_subscribers={TIER_PRO: 1})
  pro = report["per_tier"][TIER_PRO]
  # 2 unique watermarks despite 3 outcomes
  assert pro["watermark_count"] == 2
  assert all(w.startswith("wm_pro_") for w in pro["watermarks"])


def test_royalty_report_defaults_tier_to_pro_when_missing():
  outcomes = [dict(_sig(), status="tp1_hit")]  # no license_tier key
  report = royalty_report(outcomes, active_subscribers={TIER_PRO: 1})
  assert report["per_tier"][TIER_PRO]["wins"] == 1


def test_build_report_populates_all_tiers_when_no_tier_specified(tmp_path, monkeypatch):
  # Isolate report + data dirs
  monkeypatch.chdir(tmp_path)
  signals = [_sig(timeframe="1d"), _sig(timeframe="1h", symbol="ETH/USDT")]
  outcomes = [_out("tp1_hit"), _out("sl_hit")]
  report = build_report(signals=signals, outcomes=outcomes, subscribers={TIER_PRO: 2}, months=1)
  assert set(report["tier_scope"]) == set(ALL_TIERS)
  assert report["input"]["signal_count"] == 2
  assert report["input"]["outcome_count"] == 2
  # Free tier drops the 1h signal
  assert len(report["licensed_signals"][TIER_FREE]) == 1
  # Pro tier keeps both
  assert len(report["licensed_signals"][TIER_PRO]) == 2


def test_build_report_scoped_to_single_tier():
  report = build_report(
    tier=TIER_ENTERPRISE,
    signals=[_sig(timeframe="1d")],
    outcomes=[],
    subscribers={TIER_ENTERPRISE: 1},
    months=1,
  )
  assert report["tier_scope"] == [TIER_ENTERPRISE]
  assert set(report["licensed_signals"]) == {TIER_ENTERPRISE}


def test_run_monetize_report_writes_json_and_md(tmp_path, monkeypatch):
  json_path = tmp_path / "out" / "report.json"
  md_path = tmp_path / "reports" / "MON.md"
  monkeypatch.setenv("EW_MONETIZE_JSON", str(json_path))
  monkeypatch.setenv("EW_MONETIZE_MD", str(md_path))

  # Reload module-level constants so overrides take effect
  import importlib
  import engine.monetize as m
  importlib.reload(m)

  monkeypatch.chdir(tmp_path)  # empty cwd → no on-disk signals/outcomes
  result = m.run_monetize_report(tier=None, months=1)

  assert result["ok"] is True
  assert Path(result["paths"]["json"]).exists()
  assert Path(result["paths"]["md"]).exists()
  payload = json.loads(Path(result["paths"]["json"]).read_text())
  assert set(payload["tier_scope"]) == set(ALL_TIERS)
  md_text = Path(result["paths"]["md"]).read_text()
  assert "Signal Licensing" in md_text
  assert "free" in md_text and "pro" in md_text and "enterprise" in md_text

  # Reload once more so subsequent tests use default paths again
  importlib.reload(m)


def test_write_reports_returns_paths(tmp_path):
  report = build_report(
    signals=[_sig(timeframe="1d")],
    outcomes=[_out("tp1_hit")],
    subscribers={TIER_PRO: 1},
  )
  jp = tmp_path / "r.json"
  mp = tmp_path / "r.md"
  paths = write_reports(report, json_path=jp, md_path=mp)
  assert paths["json"] == str(jp)
  assert paths["md"] == str(mp)
  assert jp.exists() and mp.exists()


def test_custom_tier_policy_overrides_default():
  custom = {
    TIER_FREE: TierPolicy(
      tier=TIER_FREE,
      monthly_price_aud=0.0,
      royalty_pct_of_r=0.0,
      tf_allowlist=frozenset({"1w"}),
      max_signals_per_day=1,
    ),
    TIER_PRO: TierPolicy(
      tier=TIER_PRO,
      monthly_price_aud=100.0,
      royalty_pct_of_r=0.0,
    ),
    TIER_ENTERPRISE: TierPolicy(
      tier=TIER_ENTERPRISE,
      monthly_price_aud=999.0,
      royalty_pct_of_r=0.25,
    ),
  }
  sigs = [_sig(timeframe="1d"), _sig(timeframe="1w")]
  free = apply_license(sigs, TIER_FREE, policies=custom)
  assert len(free) == 1
  assert free[0]["timeframe"] == "1w"
  outcomes = [_out("tp1_hit", license_tier=TIER_ENTERPRISE)]
  report = royalty_report(outcomes, tier_policy=custom, active_subscribers={TIER_ENTERPRISE: 3}, months=1)
  assert report["per_tier"][TIER_ENTERPRISE]["subscription_revenue_aud"] == pytest.approx(2997.0)
  assert report["per_tier"][TIER_ENTERPRISE]["royalty_r"] == pytest.approx(0.25)
