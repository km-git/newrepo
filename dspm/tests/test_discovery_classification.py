from pathlib import Path

from dspm.classification.service import classify_csv
from dspm.discovery.service import discover_directory


def test_discover_directory_finds_csv():
    root = Path(__file__).resolve().parents[1]
    stores = discover_directory(root / "examples")
    assert len(stores) >= 1
    assert any(s.store_type == "csv" for s in stores)


def test_classify_sample_csv_has_findings():
    root = Path(__file__).resolve().parents[1]
    findings = classify_csv(root / "examples" / "sample.csv", max_rows=20)
    assert len(findings) >= 5
    types = {f.type for f in findings}
    assert "PII" in types or any(f.verdict == "PII" for f in findings)
