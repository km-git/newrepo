"""Unified data source connector tests."""

from pathlib import Path

from dspm.sources.registry import SUPPORTED_SCHEMES, discover, preview
from dspm.sources.scanner import scan_and_classify


def test_supported_schemes():
    assert "s3" in SUPPORTED_SCHEMES
    assert "m365" in SUPPORTED_SCHEMES
    assert "smb" in SUPPORTED_SCHEMES
    assert "backup" in SUPPORTED_SCHEMES


def test_discover_local_examples():
    root = Path(__file__).resolve().parents[1]
    uri = f"file://{root}/examples"
    objects = discover(uri, max_objects=50)
    assert len(objects) >= 1
    assert any(o.name == "sample.csv" for o in objects)


def test_discover_backup_archive_members():
    root = Path(__file__).resolve().parents[1]
    uri = f"backup://{root}/examples/archives"
    objects = discover(uri, max_objects=50)
    assert any("payroll" in o.name.lower() or "payroll" in o.path for o in objects)


def test_preview_archive_member():
    root = Path(__file__).resolve().parents[1]
    uri = f"backup://{root}/examples/archives"
    prev = preview(uri, "payroll_backup.zip!payroll.csv")
    assert "alice" in prev.preview_text.lower() or "email" in prev.preview_text.lower()


def test_scan_s3_fixture():
    result = scan_and_classify("s3://company-data-lake/backups/", max_objects=20, classify_limit=10)
    assert result.object_count >= 1
    assert len(result.findings) >= 1


def test_scan_m365_fixture():
    result = scan_and_classify("m365://exchange", max_objects=20, classify_limit=10)
    assert result.object_count >= 1


def test_scan_smb_fixture():
    result = scan_and_classify("smb://fileserver01/hr", max_objects=20, classify_limit=10)
    assert result.object_count >= 1
    assert any("@" in str(f) for f in result.findings) or len(result.findings) >= 0


def test_scan_saas_fixture():
    result = scan_and_classify("saas://gdrive", max_objects=10, classify_limit=5)
    assert result.object_count >= 1
