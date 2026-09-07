"""Repo-relative paths for the cost package."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
OUTPUT_DIR = REPO_ROOT / "output" / "cost"
REPORTS_DIR = REPO_ROOT / "reports"
DISCLAIMER_PATH = REPO_ROOT / "disclaimers" / "disclaimer_au.txt"
SCHEMA_PATH = PACKAGE_ROOT / "db" / "schema.sql"
FIXTURES_PATH = PACKAGE_ROOT / "fixtures" / "sandbox.json"
TAGGING_POLICY_PATH = PACKAGE_ROOT / "tagging-policy.yaml"
FRAMEWORKS_DIR = PACKAGE_ROOT / "frameworks"
REMEDIATION_DIR = PACKAGE_ROOT / "remediation"
TEMPLATES_DIR = PACKAGE_ROOT / "templates"
MONTHLY_DIR = REPO_ROOT / "monthly"
STATIC_HTML = REPORTS_DIR / "cost_explorer.html"
DEFAULT_DB = OUTPUT_DIR / "cost.sqlite3"
INVENTORY_JSON = OUTPUT_DIR / "cost-inventory.json"
REPORT_MD = OUTPUT_DIR / "report.md"
REPORT_JSON = OUTPUT_DIR / "report.json"
PROWLER_OUT = PACKAGE_ROOT / "prowler-out"


def db_path() -> Path:
    raw = os.environ.get("COST_DB", "").strip()
    return Path(raw) if raw else DEFAULT_DB


def ensure_output() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    PROWLER_OUT.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
