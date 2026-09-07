"""Live tape-to-cloud ingest: real file bytes, not sample ACME JSON."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from engine.tape_to_cloud_hub import dispatch_tape_to_cloud
from tape_to_cloud.cli import main as tape_cli
from tape_to_cloud.ingest import ingest, restore_job, try_delete_job_object, verify_job
from tape_to_cloud.integrity import sha256_file
from tape_to_cloud.jobs import list_jobs, load_job
from tape_to_cloud.store import object_path
from tape_to_cloud.worm import WormLockedError

EML = (
    b"From: custodian@example.com\r\n"
    b"To: counsel@example.com\r\n"
    b"Subject: Hold notice 4412\r\n"
    b"Date: Mon, 7 Sep 2026 10:00:00 +0000\r\n"
    b"Message-ID: <hold-4412@example.com>\r\n"
    b"\r\n"
    b"Preserve mailbox for matter HOLD-4412.\r\n"
)


def _write_source(root: Path) -> Path:
    src = root / "export"
    nested = src / "nested"
    nested.mkdir(parents=True)
    (nested / "memo.txt").write_bytes(b"real memo bytes for HOLD-4412\n")
    (src / "note.eml").write_bytes(EML)
    (src / "secret.enc").write_bytes(b"\x00opaque-ciphertext-not-plaintext")
    tar_path = src / "bundle.tar"
    with tarfile.open(tar_path, "w") as archive:
        payload = b"tar member body\n"
        info = tarfile.TarInfo(name="inside.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    return src


def test_ingest_hashes_real_bytes_refuses_enc_and_extracts_eml(tmp_path, monkeypatch):
    store = tmp_path / "store"
    monkeypatch.setenv("EW_TAPE_STORE", str(store))
    src = _write_source(tmp_path)
    expected_memo = sha256_file(src / "nested" / "memo.txt")
    expected_eml = sha256_file(src / "note.eml")
    expected_tar = sha256_file(src / "bundle.tar")

    report = ingest(
        src,
        store=store,
        matter_id="HOLD-4412",
        keyword="HOLD-4412",
        worm_until="2033-12-31T00:00:00+00:00",
    )

    assert report["sample"] is False
    assert report["kind"] == "live_ingest"
    assert report["matter_id"] == "HOLD-4412"
    assert report["status"] == "partial"
    assert report["hash_algorithm"] == "SHA-256"
    assert "MD5" in report["refused_hash_algorithms"]
    assert report["object_count"] == 3
    paths = {obj["path"]: obj for obj in report["objects"]}
    assert paths["nested/memo.txt"]["sha256"] == expected_memo
    assert paths["note.eml"]["sha256"] == expected_eml
    assert paths["bundle.tar"]["sha256"] == expected_tar
    assert paths["nested/memo.txt"]["match"] is True
    assert paths["bundle.tar"]["format_reader"] == "tarfile"
    assert "inside.txt" in paths["bundle.tar"]["tar_members"]
    assert report["failures"] == [{"path": "secret.enc", "error": "encrypted-without-keys", "action": "STOP_AND_ASK"}]
    assert report["email_hits"] >= 1
    assert report["worm"]["locked"] is True
    stored_memo = store / "objects" / expected_memo[:2] / expected_memo
    assert stored_memo.is_file()
    assert sha256_file(stored_memo) == expected_memo
    assert (store / "jobs" / report["id"] / "coc.jsonl").is_file()
    assert (store / "jobs" / report["id"] / "email_production.json").is_file()

    verified = verify_job(report["id"], store=store)
    assert verified["objects_ok"] is True
    assert verified["report_hash_ok"] is True
    assert verified["mismatches"] == []

    dest = tmp_path / "restored"
    restored = restore_job(report["id"], dest, store=store)
    restored_memo = dest / "nested" / "memo.txt"
    assert restored_memo.is_file()
    assert restored_memo.read_bytes() == b"real memo bytes for HOLD-4412\n"
    assert sha256_file(restored_memo) == expected_memo
    assert len(restored["restored"]) == 3

    with pytest.raises(WormLockedError):
        try_delete_job_object(report["id"], expected_memo, store=store)
    assert stored_memo.is_file()

    jobs = list_jobs(store)
    assert jobs[0]["id"] == report["id"]
    assert jobs[0]["sample"] is False
    loaded = load_job(report["id"], store)
    assert loaded is not None
    assert loaded["canonical_sha256"] == report["canonical_sha256"]


def test_verify_detects_tampered_object_bytes(tmp_path, monkeypatch):
    store = tmp_path / "store"
    monkeypatch.setenv("EW_TAPE_STORE", str(store))
    src = tmp_path / "one.bin"
    src.write_bytes(b"original-bytes")
    report = ingest(src, store=store, matter_id="TAMPER")
    digest = report["objects"][0]["sha256"]
    target = store / "objects" / digest[:2] / digest
    target.write_bytes(b"tampered-bytes")
    result = verify_job(report["id"], store=store)
    assert result["objects_ok"] is False
    assert digest in result["mismatches"]


def test_enc_with_unwrap_key_still_stored_opaque(tmp_path, monkeypatch):
    store = tmp_path / "store"
    monkeypatch.setenv("EW_TAPE_STORE", str(store))
    blob = tmp_path / "secret.enc"
    blob.write_bytes(b"\xffciphertext")
    key = tmp_path / "unwrap.key"
    key.write_bytes(b"not-a-bypass-just-present")
    report = ingest(blob, store=store, matter_id="ENC", unwrap_key=key)
    assert report["object_count"] == 1
    obj = report["objects"][0]
    assert obj["opaque_ciphertext"] is True
    assert obj["unwrap_key_sha256"] == sha256_file(key)
    assert obj["sha256"] == sha256_file(blob)


def test_cli_ingest_verify_restore_status(tmp_path, monkeypatch, capsys):
    store = tmp_path / "store"
    monkeypatch.setenv("EW_TAPE_STORE", str(store))
    src = tmp_path / "hello.txt"
    src.write_bytes(b"cli-real-bytes")
    rc = tape_cli(["--store", str(store), "ingest", str(src), "--matter", "CLI"])
    ingest_out = capsys.readouterr().out
    assert rc == 0
    report = json.loads(ingest_out)
    job_id = report["id"]
    assert report["sample"] is False
    assert report["object_count"] == 1

    assert tape_cli(["--store", str(store), "verify", job_id]) == 0
    capsys.readouterr()
    dest = tmp_path / "out"
    assert tape_cli(["--store", str(store), "restore", job_id, str(dest)]) == 0
    capsys.readouterr()
    assert (dest / "hello.txt").read_bytes() == b"cli-real-bytes"
    assert tape_cli(["--store", str(store), "status"]) == 0
    listing = json.loads(capsys.readouterr().out)
    assert listing["jobs"][0]["id"] == job_id
    assert listing["jobs"][0]["sample"] is False


def test_ew_tool_tape_ingest_does_not_require_symbol(tmp_path):
    store = tmp_path / "store"
    src = tmp_path / "payload.bin"
    src.write_bytes(b"ew-tool-ingest-bytes")
    proc = subprocess.run(
        [
            sys.executable,
            "ew_tool.py",
            "--tape-ingest",
            str(src),
            "--tape-matter",
            "EWTOOL",
            "--tape-store",
            str(store),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["sample"] is False
    assert report["matter_id"] == "EWTOOL"
    assert report["objects"][0]["sha256"] == sha256_file(src)
    status = subprocess.run(
        [sys.executable, "ew_tool.py", "--tape-status", "--tape-store", str(store)],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    assert status.returncode == 0, status.stderr
    listing = json.loads(status.stdout)
    assert listing["jobs"][0]["id"] == report["id"]


def test_hub_lists_live_job_not_sample(tmp_path, monkeypatch):
    store = tmp_path / "store"
    monkeypatch.setenv("EW_TAPE_STORE", str(store))
    src = tmp_path / "live.txt"
    src.write_bytes(b"hub-visible-bytes")
    report = ingest(src, store=store, matter_id="HUB")
    jobs_api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/jobs")
    assert jobs_api is not None
    payload = json.loads(jobs_api[2])
    assert payload["count"] >= 1
    assert payload["jobs"][0]["id"] == report["id"]
    assert payload["jobs"][0]["sample"] is False
    page = dispatch_tape_to_cloud("GET", f"/tape-to-cloud/jobs/{report['id']}")
    assert page is not None
    assert page[0] == 200
    assert b"sample=False" in page[2] or b"sample=false" in page[2]
    assert report["id"].encode() in page[2]
    hub = dispatch_tape_to_cloud("GET", "/tape-to-cloud")
    assert hub is not None
    assert report["id"].encode() in hub[2]
    assert b"Live ingest jobs (real bytes)" in hub[2]


def test_job_id_and_digest_cannot_escape_store(tmp_path, monkeypatch):
    store = tmp_path / "store"
    monkeypatch.setenv("EW_TAPE_STORE", str(store))
    src = tmp_path / "ok.txt"
    src.write_bytes(b"safe")
    report = ingest(src, store=store, matter_id="SAFE")

    assert load_job("../etc/passwd", store) is None
    assert load_job("job-not-a-real-id", store) is None
    assert load_job(report["id"], store) is not None

    with pytest.raises(ValueError, match="invalid job id"):
        restore_job("../../etc", tmp_path / "out", store=store)
    with pytest.raises(ValueError, match="invalid sha256"):
        object_path(store, "../../etc/passwd")
    with pytest.raises(ValueError, match="invalid sha256"):
        object_path(store, "deadbeef")

    missing = dispatch_tape_to_cloud("GET", "/tape-to-cloud/jobs/..")
    assert missing is not None
    assert missing[0] == 404
    missing = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/jobs/../../etc/passwd")
    assert missing is not None
    assert missing[0] == 404


def test_hub_escapes_html_in_live_job_json(tmp_path, monkeypatch):
    store = tmp_path / "store"
    monkeypatch.setenv("EW_TAPE_STORE", str(store))
    src = tmp_path / "<img src=x onerror=alert(1)>.txt"
    src.write_bytes(b"xss-probe")
    report = ingest(src, store=store, matter_id="<script>alert(1)</script>")
    page = dispatch_tape_to_cloud("GET", f"/tape-to-cloud/jobs/{report['id']}")
    assert page is not None
    body = page[2].decode("utf-8")
    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    assert "&lt;img" in body
