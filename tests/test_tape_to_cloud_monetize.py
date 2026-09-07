"""Smoke tests for tape_to_cloud.monetize (license tagging + royalties)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_license_tag_roundtrip(tmp_path: Path) -> None:
    from tape_to_cloud.monetize.licensing import LICENSE_CLASSES, LicenseStore, LicenseTag

    store = LicenseStore(tmp_path)
    tag = LicenseTag(
        asset_id="doc-001",
        license_id="CC-BY-4.0",
        license_class=LICENSE_CLASSES[0],
        rights=("read",),
        territory="global",
        expires_at=None,
        attribution_required=True,
        source_manifest_sha256="a" * 64,
        licensor_id="licensor-1",
    )
    store.add_tag(tag, actor="test")
    loaded = store.latest_tag_for_asset("doc-001")
    assert loaded is not None
    assert loaded.license_id == "CC-BY-4.0"


def test_monetize_cli_tag_subcommand(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tape_to_cloud.monetize",
            "--store",
            str(tmp_path),
            "tag",
            "--asset-id",
            "asset-x",
            "--license-id",
            "MIT",
            "--license-class",
            "commercially-licensable",
            "--right",
            "read",
            "--territory",
            "global",
            "--manifest-sha256",
            "b" * 64,
            "--licensor-id",
            "tester",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["asset_id"] == "asset-x"
    assert (tmp_path / "license_manifest.json").exists()
