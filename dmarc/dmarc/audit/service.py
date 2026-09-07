"""Audit module — workspace + OSS tool inventory."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone

from dmarc.config import PKG_ROOT, PROJECT_ROOT
from dmarc.db import init_db
from dmarc.models import OssToolInfo

MODULES = [
    "audit",
    "dns_check",
    "spf_parser",
    "dkim_check",
    "dmarc_ingest",
    "aggregate_report",
    "forensic_report",
    "inbox_placement",
    "report_writer",
    "loop",
    "web",
    "elastic_stack",
]

PRIMARY_OSS_TOOLS = [
    ("dnspython", "BSD-3-Clause", "dns_check"),
    ("cryptography", "Apache-2.0 OR BSD-3-Clause", "dkim_check"),
    ("parsedmarc", "MIT", "dmarc_ingest"),
    ("duckdb", "MIT", "aggregate_report"),
    ("plotly", "MIT", "aggregate_report"),
    ("presidio-analyzer", "MIT", "forensic_report"),
    ("aiosmtplib", "MIT", "inbox_placement"),
    ("jinja2", "BSD-3-Clause", "report_writer"),
    ("fastapi", "MIT", "web"),
    ("typer", "MIT", "audit"),
]


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _pip_audit_summary() -> list[dict]:
    try:
        proc = subprocess.run(
            ["pip-audit", "-f", "json"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return []


def build_inventory() -> dict:
    init_db()
    tools: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()
    for name, license_, module in PRIMARY_OSS_TOOLS:
        tools.append(
            OssToolInfo(
                name=name,
                version=_pkg_version(name.replace("_", "-")),
                license=license_,
                module=module,
                last_update=now,
            ).model_dump()
        )
    inventory = {
        "generated_at": now,
        "project": "dmarc",
        "version": importlib.metadata.version("dmarc") if _pkg_version("dmarc") != "not-installed" else "0.1.0",
        "modules": MODULES,
        "tools": tools,
        "pip_audit": _pip_audit_summary(),
        "paths": {
            "project_root": str(PROJECT_ROOT),
            "package_root": str(PKG_ROOT),
        },
    }
    out = PROJECT_ROOT / "dmarc-inventory.json"
    out.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory
