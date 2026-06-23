"""Tests for MSB entry hard block."""

from __future__ import annotations

from core.msb_zscore import msb_allows_entry, msb_blocks_entry


def test_msb_pass_blocks_entry():
  msb = {"status": "ok", "pass": True, "z": 2.0}
  assert msb_blocks_entry(msb) is True
  assert msb_allows_entry(msb) is False


def test_msb_weak_allows_entry():
  msb = {"status": "ok", "pass": False, "z": 0.5}
  assert msb_blocks_entry(msb) is False
  assert msb_allows_entry(msb) is True


def test_msb_no_data_allows_entry():
  assert msb_blocks_entry({"status": "no_break", "pass": False}) is False
  assert msb_allows_entry(None) is True
