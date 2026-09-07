"""Tests for tape-to-cloud cross-cutting layers and CLI."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tape_to_cloud.layers import (
    LayerError,
    apply_format_readers,
    apply_kms_kmip,
    apply_layers,
    apply_media_rescue,
    sha256_hex,
)
from tape_to_cloud.sample_reports import get_report


def test_apply_layers_sha256_covers_result():
    result = {"hello": "world"}
    block = apply_layers("audit", result)
    assert set(block) == {
        "integrity",
        "ediscovery",
        "kms-kmip",
        "worm",
        "format-readers",
        "media-rescue",
    }
    assert block["integrity"]["primary_algo"] == "SHA-256"
    assert block["integrity"]["md5_not_primary"] is True
    assert len(block["integrity"]["pre_hash"]) == 64
    again = apply_layers("audit", result)
    assert again["integrity"]["pre_hash"] == block["integrity"]["pre_hash"]
    assert apply_layers("audit", {"hello": "other"})["integrity"]["pre_hash"] != block["integrity"]["pre_hash"]
    assert sha256_hex("x") != block["integrity"]["pre_hash"]


def test_kmip_refuses_missing_key():
    with pytest.raises(LayerError, match="refuse read"):
        apply_kms_kmip(key_present=False)


def test_format_reader_refuses_invented_parser():
    with pytest.raises(LayerError, match="license-or-wrap"):
        apply_format_readers(plugin="invent-tsm-header-parser")


def test_media_rescue_refuses_crypto_bypass():
    with pytest.raises(LayerError, match="crypto bypass"):
        apply_media_rescue(crypto_bypass_attempted=True)


def test_sample_report_layers_come_from_engine():
    report = get_report("audit")
    expected = apply_layers("audit", report["result"])
    assert report["layers"] == expected
    assert report["layers"]["worm"]["erasure_conflict"] == "stop-and-ask"


def test_cli_report_audit():
    proc = subprocess.run(
        [sys.executable, "-m", "tape_to_cloud", "report", "audit"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["module"] == "audit"
    assert payload["layers"]["integrity"]["primary_algo"] == "SHA-256"


def test_cli_list_json():
    proc = subprocess.run(
        [sys.executable, "-m", "tape_to_cloud", "list", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    rows = json.loads(proc.stdout)
    assert len(rows) == 17
    assert any(row["module"] == "audit" for row in rows)
