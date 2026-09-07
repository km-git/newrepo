"""Architecture tests for the 10-module cost mosaic."""

from pathlib import Path

import cost
from cost import MODULES, OSS_PRIMARY_TOOLS


def test_module_count():
    assert len(MODULES) >= 10
    assert "audit" in MODULES
    assert "report_writer" in MODULES
    assert "webui" in MODULES


def test_primary_tools():
    assert "steampipe" in OSS_PRIMARY_TOOLS
    assert "duckdb" in OSS_PRIMARY_TOOLS


def test_schema_tables():
    schema = Path("cost/db/schema.sql").read_text(encoding="utf-8")
    for table in (
        "findings_resources",
        "findings_costs",
        "findings_rightsizing",
        "findings_untagged",
        "findings_drift",
        "findings_compliance",
        "tenants",
    ):
        assert table in schema


def test_disclaimer_exists():
    assert Path("disclaimers/disclaimer_au.txt").exists()


def test_version():
    assert cost.__version__ == "0.1.0"
