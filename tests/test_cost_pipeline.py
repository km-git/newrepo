"""End-to-end sandbox tests for the Cloud Cost & Configuration Review."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from cost.language import contains_banned
from cost.pipeline import run_all
from cost.subprocess_tools import ALLOWED_BINARIES

ROOT = Path(__file__).resolve().parents[1]


def test_scan_all_sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("COST_SANDBOX", "1")
    monkeypatch.setenv("COST_DB", str(tmp_path / "cost.sqlite3"))
    monkeypatch.chdir(ROOT)
    result = run_all(sandbox=True, provider="all", since="30d")
    assert result["ok"] is True
    assert result["inventory"]["tool_count"] >= 8
    assert result["aws"]["provider"] == "aws"
    assert result["azure"]["provider"] == "azure"
    assert result["gcp"]["provider"] == "gcp"
    assert result["costs"]["rows"]
    assert result["rightsizing"]["findings"]
    assert result["untagged"]["findings"]
    assert result["drift"]["findings"]
    assert result["framework"]["rows"]
    assert result["multi_account"]["dryrun"] is True
    report = result["report"]["markdown"]
    assert "Cloud Cost & Configuration Review" in report
    assert "Liability disclaimer" in report or "liability disclaimer" in report.lower()
    assert contains_banned(report) == []
    assert "review with the engineering team" in report.lower()
    assert Path(result["report"]["markdown_path"]).is_file()
    assert Path(result["monthly"]["trend"]).is_file()
    inv = json.loads((ROOT / "output" / "cost" / "cost-inventory.json").read_text())
    assert inv["steampipe_import_forbidden"] is True


def test_cli_scan_all(tmp_path, monkeypatch):
    monkeypatch.setenv("COST_SANDBOX", "1")
    monkeypatch.setenv("COST_DB", str(tmp_path / "cost.sqlite3"))
    from cost.cli import main

    rc = main(["scan-all", "--provider", "all"])
    assert rc == 0


def test_steampipe_never_imported():
    for path in ROOT.joinpath("cost").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] != "steampipe", path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] != "steampipe", path


def test_steampipe_allowlist_is_cli_only():
    assert "steampipe" in ALLOWED_BINARIES
    assert "prowler" in ALLOWED_BINARIES
    assert "trivy" in ALLOWED_BINARIES


def test_c7n_policies_are_dryrun():
    folder = ROOT / "cost" / "remediation"
    files = list(folder.glob("c7n-*.yaml"))
    assert len(files) == 4
    text = "\n".join(p.read_text(encoding="utf-8") for p in files)
    assert "dryrun: true" in text
    assert "c7n-stop-unencrypted-rds.yaml" in {p.name for p in files}
    assert "c7n-tag-untagged-resources.yaml" in {p.name for p in files}
    assert "c7n-rightsizing-recommendation.yaml" in {p.name for p in files}
    assert "c7n-cost-anomaly-alert.yaml" in {p.name for p in files}


def test_ten_modules_exist():
    names = (
        "audit",
        "aws_inventory",
        "azure_inventory",
        "gcp_inventory",
        "cost_explorer",
        "rightsizing",
        "untagged",
        "config_drift",
        "compliance_map",
        "report_writer",
    )
    for name in names:
        mod = ROOT / "cost" / name
        assert (mod / "cli.py").is_file()
        assert (mod / "service.py").is_file()
        assert (mod / "models.py").is_file()
        assert (mod / "README.md").is_file()
        words = len((mod / "README.md").read_text().split())
        assert words <= 200, name
