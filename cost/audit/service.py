"""cost/audit — workspace + OSS tool inventory."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from cost.db.store import init_schema
from cost.paths import INVENTORY_JSON, PACKAGE_ROOT, REPO_ROOT, ensure_output
from cost.subprocess_tools import trivy_version, which

TOOLS = (
    {"name": "duckdb", "license": "MIT", "last_update": "2025-12-01", "invocation": "python-library", "pypi": "duckdb"},
    {
        "name": "steampipe",
        "license": "AGPL-3.0",
        "last_update": "2026-01-15",
        "invocation": "cli-subprocess",
        "version": "2.4.4",
        "note": "never import; CLI only",
    },
    {
        "name": "boto3",
        "license": "Apache-2.0",
        "last_update": "2025-09-01",
        "invocation": "python-library",
        "pypi": "boto3",
    },
    {
        "name": "azure-mgmt-resource",
        "license": "MIT",
        "last_update": "2025-06-01",
        "invocation": "python-library",
        "pypi": "azure-mgmt-resource",
    },
    {
        "name": "google-cloud-resource-manager",
        "license": "Apache-2.0",
        "last_update": "2025-06-01",
        "invocation": "python-library",
        "pypi": "google-cloud-resource-manager",
    },
    {
        "name": "c7n",
        "license": "Apache-2.0",
        "last_update": "2026-05-28",
        "invocation": "cli-subprocess",
        "pypi": "c7n",
        "note": "PyPI name is c7n, not cloud-custodian",
    },
    {
        "name": "c7n-org",
        "license": "Apache-2.0",
        "last_update": "2026-05-28",
        "invocation": "cli-subprocess",
        "pypi": "c7n-org",
    },
    {
        "name": "prowler",
        "license": "Apache-2.0",
        "last_update": "2026-09-01",
        "invocation": "cli-subprocess",
        "version": "5.41.0",
    },
    {
        "name": "trivy",
        "license": "Apache-2.0",
        "last_update": "2026-04-01",
        "invocation": "cli-subprocess",
        "version": "0.71.2",
        "note": "never v0.69.4 CVE-2026-33634",
    },
    {
        "name": "presidio-analyzer",
        "license": "MIT",
        "last_update": "2026-01-01",
        "invocation": "python-library",
        "pypi": "presidio-analyzer",
        "note": "install from data-privacy-stack/presidio",
    },
    {
        "name": "pip-audit",
        "license": "Apache-2.0",
        "last_update": "2025-12-01",
        "invocation": "cli-subprocess",
        "pypi": "pip-audit",
    },
    {
        "name": "jinja2",
        "license": "BSD-3-Clause",
        "last_update": "2025-01-01",
        "invocation": "python-library",
        "pypi": "Jinja2",
    },
)


def _pkg_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _on_path(name: str) -> bool:
    try:
        return which(name) is not None
    except ValueError:
        return False


def run(*, sandbox: bool = True, **_kwargs: Any) -> dict[str, Any]:
    init_schema()
    ensure_output()
    items = []
    for spec in TOOLS:
        version = spec.get("version") or (_pkg_version(spec["pypi"]) if spec.get("pypi") else None) or "not-installed"
        if spec["name"] == "trivy":
            detected = trivy_version()
            if detected:
                version = detected
        items.append(
            {
                "name": spec["name"],
                "version": version,
                "license": spec["license"],
                "last_update": spec["last_update"],
                "invocation": spec["invocation"],
                "on_path": _on_path(spec["name"])
                if spec["invocation"] == "cli-subprocess"
                else spec.get("pypi") is not None,
                "note": spec.get("note", ""),
            }
        )
    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "python": sys.version.split()[0],
        "package_root": str(PACKAGE_ROOT),
        "repo_root": str(REPO_ROOT),
        "tool_count": len(items),
        "tools": items,
        "sandbox": sandbox,
        "steampipe_import_forbidden": True,
    }
    path: Path = INVENTORY_JSON
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    payload["path"] = str(path)
    return payload
