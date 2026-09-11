"""Filesystem layout for the deliverability toolkit."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
DISCLAIMER_PATH = PACKAGE_ROOT / "disclaimers" / "disclaimer_au.txt"
SELECTORS_PATH = PACKAGE_ROOT / "templates" / "selectors.yaml"
REPORT_TEMPLATE = PACKAGE_ROOT / "templates" / "report.md.j2"
EXPLORER_TEMPLATE = PACKAGE_ROOT / "templates" / "explorer.html"
SCHEMA_SQL = PACKAGE_ROOT / "db" / "schema.sql"
PARSEDMARC_INI = PACKAGE_ROOT / "parsedmarc.ini"
FIXTURES = PACKAGE_ROOT / "fixtures"
RUA_FIXTURES = FIXTURES / "rua"
RUF_FIXTURES = FIXTURES / "ruf"
SEEDS_PATH = PACKAGE_ROOT / "templates" / "seed_accounts.yaml"

DEFAULT_OUTPUT = Path(os.environ.get("DMARC_OUTPUT_DIR", "output/dmarc"))
STATIC_EXPLORER = Path("reports/dmarc_explorer.html")
MONTHLY_DIR = Path(os.environ.get("DMARC_MONTHLY_DIR", "monthly"))


def output_dir(override: str | Path | None = None) -> Path:
    path = Path(override) if override else DEFAULT_OUTPUT
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path(root: Path | None = None) -> Path:
    return output_dir(root) / "dmarc.sqlite3"


def inventory_path(root: Path | None = None) -> Path:
    return output_dir(root) / "dmarc-inventory.json"
