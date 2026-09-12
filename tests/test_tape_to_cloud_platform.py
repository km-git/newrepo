"""Tests for tape-to-cloud platform core and web API."""

from __future__ import annotations

import json
from pathlib import Path

from engine.tape_to_cloud_hub import build_hub_state, dispatch_tape_to_cloud
from tape_to_cloud.core import MODULES, PlatformContext
from tape_to_cloud.core.layers import apply_kms_kmip, apply_worm
from tape_to_cloud.core.manifests import build_file_manifest, sha256_file
from tape_to_cloud.core.registry import list_modules, submit_and_run
from tape_to_cloud.web.api import handle_api, platform_status


def test_sixteen_modules_registered():
    mods = list_modules()
    assert len(mods) == 16
    assert {m["id"] for m in mods} == set(MODULES)


def test_sha256_and_manifest(tmp_path: Path):
    sample = tmp_path / "data.bin"
    sample.write_bytes(b"tape-to-cloud-test")
    digest = sha256_file(sample)
    assert len(digest) == 64
    manifest = build_file_manifest([sample], job_id="j1", module="audit", root=tmp_path)
    assert manifest["file_count"] == 1
    assert manifest["files"][0]["sha256"] == digest


def test_layers_kms_refuse_without_key():
    import pytest

    with pytest.raises(PermissionError):
        apply_kms_kmip(encrypt=True)


def test_layers_worm_erasure_conflict():
    result = apply_worm(retention_days=365, erasure_requested=True)
    assert result["action"] == "stop-and-ask"


def test_submit_and_run_audit_job(tmp_path: Path):
    ctx = PlatformContext(tmp_path)
    job = submit_and_run(ctx, "audit", {"format": "LTO-8", "barcode": "TAPE-001"})
    assert job["status"] == "completed"
    assert job["result"] is not None
    assert "audit" in job["result"]
    assert len(job["layers_applied"]) == 5


def test_disk_ingest_and_restore(tmp_path: Path):
    src = tmp_path / "ingest"
    src.mkdir()
    (src / "file.txt").write_text("hello vault", encoding="utf-8")
    ctx = PlatformContext(tmp_path / "platform")
    ingest = submit_and_run(ctx, "disk-ingest", {"source_path": str(src)})
    assert ingest["status"] == "completed"
    stored = ingest["result"]["disk_ingest"]["objects"]
    assert len(stored) == 1
    object_id = stored[0]["object_id"]
    restore = submit_and_run(ctx, "restore", {"object_id": object_id})
    assert restore["status"] == "completed"
    assert restore["result"]["restore"]["object_id"] == object_id


def test_platform_status(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EW_TTC_DATA_DIR", str(tmp_path))
    status = platform_status()
    assert status["module_count"] == 16
    assert len(status["cross_cutting_layers"]) == 6


def test_api_create_job(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EW_TTC_DATA_DIR", str(tmp_path))
    body = json.dumps({"module": "tape-ops", "params": {}}).encode()
    resp = handle_api("POST", "/api/tape-to-cloud/jobs", {}, body)
    assert resp is not None
    assert resp[0] == 201
    payload = json.loads(resp[2])
    assert payload["module"] == "tape-ops"
    assert payload["status"] == "completed"


def test_api_list_and_get_job(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EW_TTC_DATA_DIR", str(tmp_path))
    body = json.dumps({"module": "vtl-cloud", "params": {"backend": "seaweedfs"}}).encode()
    created = handle_api("POST", "/api/tape-to-cloud/jobs", {}, body)
    job = json.loads(created[2])
    listed = handle_api("GET", "/api/tape-to-cloud/jobs", {}, b"")
    assert listed is not None
    assert b"vtl-cloud" in listed[2]
    got = handle_api("GET", f"/api/tape-to-cloud/jobs/{job['id']}", {}, b"")
    assert got is not None
    assert json.loads(got[2])["id"] == job["id"]


def test_dispatch_platform_html():
    resp = dispatch_tape_to_cloud("GET", "/tape-to-cloud/platform")
    assert resp is not None
    assert b"Tape-to-Cloud Platform" in resp[2]


def test_hub_includes_platform_stats(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EW_TTC_DATA_DIR", str(tmp_path))
    state = build_hub_state()
    assert state["module_count"] == 16
    assert "platform" in state
    assert state["platform"]["module_count"] == 16
