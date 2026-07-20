"""Tests for asymmetric pyramiding DCA and stop-loss sanity."""

from __future__ import annotations

import pytest

from core.risk import (
  build_dca_ladder,
  compute_wae,
  dynamic_stop,
  sensible_entry_anchor,
  stop_is_sane,
)


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


def test_dca_no_duplicate_legs_mid_zone_anchor():
  """Anchor mid-zone must not collapse L1 and L2 to the same price."""
  legs = build_dca_ladder("SHORT", 73468.0, 500.0, 72842.0, 74094.0)
  prices = [l["price"] for l in legs]
  assert len(set(prices)) == 4
  assert prices[0] < prices[1] < prices[2] < prices[3]

  legs_long = build_dca_ladder("LONG", 100.0, 2.0, 95.0, 105.0)
  prices_long = [l["price"] for l in legs_long]
  assert len(set(prices_long)) == 4
  assert prices_long[0] > prices_long[1] > prices_long[2] > prices_long[3]


def test_dca_ignores_htf_fibs_outside_zone():
  legs = build_dca_ladder(
    "SHORT", 73468.0, 500.0, 72842.0, 74094.0,
    fib_levels=[110367.0, 100572.0],
  )
  assert legs[1]["price"] <= 74094.0
  assert legs[1]["price"] >= 72842.0


def test_dynamic_stop_long():
  s = dynamic_stop(
    "LONG", 100.0, 2.0, 96.0, 110.0, atr_mult=1.0,
    zone_low=95.0, zone_high=105.0, timeframe="1h", ladder_legs=build_dca_ladder("LONG", 100.0, 2.0, 95.0, 105.0),
  )
  assert s["price"] < 100.0
  assert s["price"] > 0
  assert 0.45 <= s["distance_pct"] <= 3.6


def test_dynamic_stop_short_clamps_stale_structure():
  legs = build_dca_ladder("SHORT", 3998.1, 400.0, 3978.0, 4018.0)
  s = dynamic_stop(
    "SHORT", 3998.1, 400.0, 1810.8, 17000.0, atr_mult=2.5,
    zone_low=3978.0, zone_high=4018.0, max_stop_atr=6.0,
    timeframe="1d", ladder_legs=legs,
  )
  assert s["price"] > 4018.0
  assert s["distance_pct"] <= 7.0
  assert s["price"] < 4300.0


def test_dynamic_stop_btc_short_zone_not_21pct():
  """BTC-style: stop just above zone ceiling, not 6 ATR into the ether."""
  zone_lo, zone_hi = 71801.0, 73088.0
  legs = build_dca_ladder("SHORT", 72444.0, 2500.0, zone_lo, zone_hi)
  wae = compute_wae(legs)
  s = dynamic_stop(
    "SHORT", wae, 2500.0, 60000.0, 90000.0, atr_mult=2.5,
    zone_low=zone_lo, zone_high=zone_hi, timeframe="1w", ladder_legs=legs,
  )
  assert s["price"] > zone_hi
  assert s["distance_pct"] < 12.0
  assert s["price"] < zone_hi * 1.10


def test_dynamic_stop_tokenized_not_razor_thin():
  legs = build_dca_ladder("SHORT", 348.85, 0.5, 347.0, 349.5)
  wae = compute_wae(legs)
  s = dynamic_stop(
    "SHORT", wae, 0.5, 300.0, 400.0, atr_mult=1.2,
    zone_low=347.0, zone_high=349.5, timeframe="15m", ladder_legs=legs,
  )
  assert s["distance_pct"] >= 0.30


def test_long_no_chase_peak():
  """LONG at zone top: every leg must sit below market."""
  current = 104.0
  legs = build_dca_ladder("LONG", 104.0, 2.0, 95.0, 105.0, current=current)
  for leg in legs:
    assert leg["price"] < current


def test_short_no_chase_trough():
  """SHORT at zone bottom: every leg must sit above market."""
  current = 96.0
  legs = build_dca_ladder("SHORT", 96.0, 2.0, 95.0, 105.0, current=current)
  for leg in legs:
    assert leg["price"] > current


def test_sensible_entry_anchor_long_pullback():
  anchor = sensible_entry_anchor("LONG", 348.85, 347.0, 349.5, 0.5)
  assert anchor < 348.85
  assert anchor >= 347.0


def test_sensible_entry_anchor_short_rally():
  anchor = sensible_entry_anchor("SHORT", 2.265, 2.249, 2.271, 0.024)
  assert anchor > 2.265


def test_short_above_zone_sells_rally():
  """SHORT with price above zone: legs above market, not into zone below."""
  current = 0.4606
  legs = build_dca_ladder("SHORT", 0.4606, 0.002, 0.4502, 0.4547, current=current)
  assert all(leg["price"] > current for leg in legs)
  assert legs[0]["price"] < legs[-1]["price"]


def test_stop_is_sane_rejects_negative_and_distant():
  assert not stop_is_sane("LONG", 0.395, -0.165, 0.05, max_atr=5.0, timeframe="1d", zone_low=0.35, zone_high=0.42)
  assert not stop_is_sane("SHORT", 3998.0, 17611.0, 400.0, max_atr=6.0, timeframe="1d", zone_low=3978.0, zone_high=4018.0)
  assert stop_is_sane(
    "SHORT", 0.1095, 0.1115, 0.005, max_atr=5.0,
    timeframe="15m", zone_low=0.10, zone_high=0.11,
  )
