"""End-to-end tests for discovery, classification, risk, and the CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample.csv"


def test_discover_examples_directory(tmp_path: Path) -> None:
    from dspm.db.store import FindingsStore
    from dspm.discovery.service import discover_directory

    store = FindingsStore(tmp_path / "dspm.sqlite")
    found = discover_directory(ROOT / "examples", store=store)
    kinds = {item.kind for item in found}
    assert "csv" in kinds
    assert store.fetchall("findings_stores")


def test_classify_sample_csv_finds_multiple_types() -> None:
    from dspm.classification.service import classify_path
    from dspm.constants import FINDING_TYPES, VERDICTS

    result = classify_path(SAMPLE, limit=80)
    assert result.rows_scanned == 80
    types = {f.type for f in result.findings}
    assert "PII" in types
    assert "custom" in types or "PHI" in types
    assert 5 <= len(result.findings) <= 5000
    for finding in result.findings:
        assert finding.type in FINDING_TYPES
        assert 0 <= finding.confidence <= 1
        assert finding.verdict in VERDICTS


def test_custom_types_checksums() -> None:
    from dspm.custom_types.service import test_type

    abn = test_type("au_abn", "51 824 753 556")
    assert abn["matched"] is True
    assert abn["checksum"] is True
    nhs = test_type("nhs_number", "943 476 5919")
    assert nhs["matched"] is True
    assert nhs["checksum"] is True
    tfn = test_type("au_tfn", "123 456 782")
    assert tfn["matched"] is True


def test_risk_formula_known_input_known_output() -> None:
    from dspm.risk.service import score_findings, score_vector, try_duckdb_score

    public_pii = score_vector(has_pii=True, public_exposure=True, unencrypted=True)
    assert public_pii["score"] == 90  # 30+25+15+20 blast-radius
    ranked = score_findings(json.loads((ROOT / "examples" / "risk_fixture.json").read_text(encoding="utf-8")))
    assert ranked[0].score == 90
    assert "public" in ranked[0].title.lower()
    duck = try_duckdb_score(
        [
            {
                "finding_id": "1",
                "has_pii": True,
                "public_exposure": True,
                "overprivileged": False,
                "unencrypted": True,
                "custom_type": False,
            }
        ]
    )
    if duck is not None:
        assert duck == [90]


def test_exposure_and_access_offline_fixtures() -> None:
    from dspm.access.service import map_access
    from dspm.exposure.service import scan_exposure

    exposures = scan_exposure(fixture=ROOT / "examples" / "prowler_fixture.json")
    assert any(item.public for item in exposures)
    edges = map_access(store_id="42")
    assert any(edge.overprivileged for edge in edges)


def test_remediation_plan_and_ai_scanner(tmp_path: Path) -> None:
    from dspm.ai_security.service import scan_export
    from dspm.compliance.service import map_findings
    from dspm.remediation.service import plan

    actions = plan(dry_run=True)
    assert len(actions) == 4
    assert all(item.dry_run_safe for item in actions)
    ai = scan_export(ROOT / "examples" / "prompt_log.jsonl")
    assert any(item.type in {"PII", "custom", "PHI"} for item in ai)
    assert "experimental" in ai[0].warning
    hits = map_findings([{"type": "PII"}], framework="gdpr")
    assert any(hit.status == "FAIL" for hit in hits)


def test_cli_audit_inventory_json() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "dspm", "audit", "inventory"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["product"] == "dspm"
    assert len(payload["modules"]) == 12
    assert len(payload["primary_oss_tools"]) == 8
    names = {t["name"] for t in payload["tools"]}
    assert "Trivy" in names
    assert "Steampipe" in names
    assert payload["gates"]["trivy_pin"] == "0.71.2"


def test_cli_classify_and_watch(tmp_path: Path) -> None:
    import os

    env = {**os.environ, "DSPM_DB": str(tmp_path / "db.sqlite")}
    proc = subprocess.run(
        [sys.executable, "-m", "dspm", "classify", str(SAMPLE), "--limit", "20"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["findings"]
    watch = subprocess.run(
        [sys.executable, "-m", "dspm", "loop", "watch"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
        env=env,
    )
    assert watch.returncode == 0, watch.stderr
    watched = json.loads(watch.stdout)
    assert watched["new_count"] >= 0
    if watched["new_count"]:
        assert watched["items"][0]["sha256"]
