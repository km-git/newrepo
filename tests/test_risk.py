"""Tests for asymmetric pyramiding DCA and stop-loss sanity."""

from __future__ import annotations

import pytest

from core.risk import build_dca_ladder, compute_wae, dynamic_stop, stop_is_sane


def test_dca_asymmetric_pyramid_long():
  """LONG: L1 highest, L4 lowest; weights 10/20/30/40."""
  legs = build_dca_ladder("LONG", 100.0, 2.0, 95.0, 105.0)
  assert [l["size_pct"] for l in legs] == [10, 20, 30, 40]
  assert legs[0]["price"] >= legs[1]["price"] >= legs[2]["price"] >= legs[3]["price"]
  assert legs[3]["price"] == pytest.approx(95.0)
  assert legs[0].get("rationale")


def test_dca_asymmetric_pyramid_short():
  legs = build_dca_ladder("SHORT", 100.0, 2.0, 95.0, 105.0)
  assert legs[0]["price"] <= legs[1]["price"] <= legs[2]["price"] <= legs[3]["price"]
  assert legs[3]["price"] == pytest.approx(105.0)


def test_wae_calculation():
  legs = build_dca_ladder("LONG", 371.84, 5.0, 345.76, 371.84)
  wae = compute_wae(legs)
  # WAE = weighted sum of leg prices
  expected = sum(l["price"] * l["size_pct"] / 100 for l in legs)
  assert wae == pytest.approx(expected, rel=1e-4)


def test_dca_ignores_htf_fibs_outside_zone():
  legs = build_dca_ladder(
    "SHORT", 73468.0, 500.0, 72842.0, 74094.0,
    fib_levels=[110367.0, 100572.0],
  )
  assert legs[1]["price"] <= 74094.0
  assert legs[1]["price"] >= 72842.0


def test_dynamic_stop_long():
  s = dynamic_stop("LONG", 100.0, 2.0, 96.0, 110.0, atr_mult=1.0, zone_low=95.0, zone_high=105.0)
  assert s["price"] < 100.0
  assert s["price"] > 0


def test_dynamic_stop_short_clamps_stale_structure():
  s = dynamic_stop(
    "SHORT", 3998.1, 400.0, 1810.8, 17000.0, atr_mult=2.5,
    zone_low=3978.0, zone_high=4018.0, max_stop_atr=6.0,
  )
  assert s["price"] > 3998.1
  assert s["price"] < 3998.1 + 6.0 * 400.0 + 1


def test_stop_is_sane_rejects_negative_and_distant():
  assert not stop_is_sane("LONG", 0.395, -0.165, 0.05, max_atr=5.0)
  assert not stop_is_sane("SHORT", 3998.0, 17611.0, 400.0, max_atr=6.0)
  assert stop_is_sane("SHORT", 0.1095, 0.119, 0.005, max_atr=5.0)
