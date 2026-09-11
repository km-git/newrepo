"""Sample Tape-to-Cloud reports: SHA-256 sidecars, intactness, hub routes."""

from __future__ import annotations

import json

from engine.tape_to_cloud_hub import CROSS_CUTTING, MODULES, dispatch_tape_to_cloud
from engine.tape_to_cloud_reports import (
    HASH_ALG,
    attach_canonical_hash,
    canonical_sha256,
    get_report,
    list_report_summaries,
    sample_reports,
    validate_intactness,
    verify_report_hash,
)


def test_sixteen_modules_and_six_layers_align():
    assert len(MODULES) == 16
    assert len(CROSS_CUTTING) == 6
    assert "monetize" in MODULES
    assert "integrity" in CROSS_CUTTING


def test_sample_reports_are_six_and_hashes_recompute():
    reports = sample_reports()
    assert len(reports) == 6
    ids = {r["id"] for r in reports}
    assert ids == {
        "rpt-audit-cma-2026-q1",
        "rpt-ediscovery-prod-hold-4412",
        "rpt-worm-kmip-policy-17a4",
        "rpt-restore-coc-job-8841",
        "rpt-integrity-sidecar-lto8-batch",
        "rpt-migration-volume-grid-zvt",
    }
    for report in reports:
        assert report["sample"] is True
        assert report["hash_algorithm"] == HASH_ALG
        assert verify_report_hash(report)
        assert canonical_sha256(report) == report["canonical_sha256"]
        assert len(report["canonical_sha256"]) == 64
        assert set(report["modules"]).issubset(set(MODULES))
        assert set(report["layers"]).issubset(set(CROSS_CUTTING))


def test_canonical_hash_detects_tamper():
    report = dict(get_report("rpt-audit-cma-2026-q1"))
    assert verify_report_hash(report)
    report["title"] = "tampered"
    assert verify_report_hash(report) is False
    repaired = attach_canonical_hash(report)
    assert verify_report_hash(repaired)


def test_media_audit_has_rfid_and_degradation():
    report = get_report("rpt-audit-cma-2026-q1")
    carts = report["body"]["cartridges"]
    assert carts[0]["rfid_epc"].startswith("E280")
    assert carts[0]["degradation"] == 3
    assert carts[0]["pre_sha256"] == carts[0]["post_sha256"]
    assert "stiction" in carts[1]["flags"]
    assert "encrypted-without-keys" in carts[2]["flags"]
    assert "MD5" in report["body"]["refused_hash_algorithms"]


def test_ediscovery_gdpr_is_stop_and_ask():
    report = get_report("rpt-ediscovery-prod-hold-4412")
    assert report["body"]["legal_hold"]["active"] is True
    assert report["body"]["gdpr_conflict"]["action"] == "STOP_AND_ASK"
    formats = {p["format"] for p in report["body"]["packages"]}
    assert formats == {"PST", "NSF", "load_file"}


def test_worm_kmip_seaweedfs_not_minio_ce():
    report = get_report("rpt-worm-kmip-policy-17a4")
    assert report["body"]["retention"]["on_prem_default"] == "SeaweedFS"
    assert report["body"]["kmip"]["refuse_read_if_key_missing"] is True
    assert report["body"]["kmip"]["kmip_object_id"].endswith("00c0ffee4412")
    assert "key_uuid" not in report["body"]["kmip"]
    assert report["body"]["conflicts"][0]["action"] == "STOP_AND_ASK"
    assert "MinIO Community Edition" in report["body"]["minio_ce"]["recommendation"]


def test_volume_grid_totals_match_rows():
    report = get_report("rpt-migration-volume-grid-zvt")
    grid = report["body"]["grid"]
    totals = report["body"]["totals"]
    assert totals["success"] == sum(1 for v in grid if v["status"] == "SUCCESS")
    assert totals["fail"] == sum(1 for v in grid if v["status"] == "FAIL")
    assert totals["in_progress"] == sum(1 for v in grid if v["status"] == "IN_PROGRESS")
    assert {v["action"] for v in grid} == {"COPY"}


def test_validate_intactness_passes_on_repo():
    state = validate_intactness()
    assert state["ok"] is True
    assert state["checks"]["sixteen_modules"] is True
    assert state["checks"]["six_layers"] is True
    assert state["checks"]["all_report_hashes_verified"] is True
    assert state["checks"]["discovery_docs_on_disk"] is True


def test_dispatch_report_html_and_api_routes():
    index = dispatch_tape_to_cloud("GET", "/tape-to-cloud/reports")
    assert index is not None and index[0] == 200
    assert b"rpt-audit-cma-2026-q1" in index[2]
    assert b"SHA-256" in index[2]

    detail = dispatch_tape_to_cloud("GET", "/tape-to-cloud/reports/rpt-restore-coc-job-8841")
    assert detail is not None and detail[0] == 200
    assert b"RESTORE-8841" in detail[2]
    assert b"chain-of-custody" in detail[2]

    missing = dispatch_tape_to_cloud("GET", "/tape-to-cloud/reports/does-not-exist")
    assert missing is not None and missing[0] == 404

    api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/reports")
    assert api is not None and api[0] == 200
    payload = json.loads(api[2])
    assert payload["count"] == 6

    one = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/reports/rpt-integrity-sidecar-lto8-batch")
    body = json.loads(one[2])
    assert body["kind"] == "integrity_sidecar"
    assert verify_report_hash(body)

    filtered = dispatch_tape_to_cloud(
        "GET",
        "/api/tape-to-cloud/reports",
        {"kind": ["ediscovery_production"]},
    )
    filtered_payload = json.loads(filtered[2])
    assert filtered_payload["count"] == 1
    assert filtered_payload["reports"][0]["kind"] == "ediscovery_production"


def test_dispatch_validation_route():
    html = dispatch_tape_to_cloud("GET", "/tape-to-cloud/validation")
    assert html is not None and html[0] == 200
    assert b"INTACT" in html[2]

    api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/validation")
    payload = json.loads(api[2])
    assert payload["ok"] is True
    assert payload["checks"]["sample_reports"] is True


def test_list_summaries_include_verified_hrefs():
    rows = list_report_summaries()
    assert all(r["hash_verified"] for r in rows)
    assert all(r["href"].startswith("/tape-to-cloud/reports/") for r in rows)
