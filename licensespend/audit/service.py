"""Workspace + pip-audit / OSV.dev inventory for licensespend."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from typing import Any

from licensespend import MODULES, OSS_PRIMARY_TOOLS, __version__
from licensespend.audit.models import Inventory, ToolRecord
from licensespend.constants import GRAPH_SCOPES, TRIVY_MALICIOUS, TRIVY_PIN

OSS_INVENTORY = (
    {
        "name": "DuckDB",
        "package": "duckdb",
        "license": "MIT",
        "role": "unused-seat SQL",
        "extra": None,
    },
    {
        "name": "PyArrow",
        "package": "pyarrow",
        "license": "Apache-2.0",
        "role": "columnar interchange",
        "extra": None,
    },
    {
        "name": "httpx",
        "package": "httpx",
        "license": "BSD-3-Clause",
        "role": "OSV / Graph HTTP",
        "extra": None,
    },
    {
        "name": "Pydantic",
        "package": "pydantic",
        "license": "MIT",
        "role": "models",
        "extra": None,
    },
    {
        "name": "Typer",
        "package": "typer",
        "license": "MIT",
        "role": "CLI",
        "extra": None,
    },
    {
        "name": "PyYAML",
        "package": "pyyaml",
        "license": "MIT",
        "role": "pricebook / contracts",
        "extra": None,
    },
    {
        "name": "feedparser",
        "package": "feedparser",
        "license": "BSD-2-Clause",
        "role": "forum-watcher feeds",
        "extra": None,
    },
    {"name": "Rich", "package": "rich", "license": "MIT", "role": "human tables", "extra": None},
    {
        "name": "Jinja2",
        "package": "jinja2",
        "license": "BSD-3-Clause",
        "role": "HTML reclaim pack",
        "extra": None,
    },
    {
        "name": "pip-audit",
        "package": "pip-audit",
        "license": "Apache-2.0",
        "role": "OSV.dev advisory scan",
        "extra": "dev",
    },
    {
        "name": "Microsoft Graph SDK",
        "package": "msgraph-sdk",
        "license": "MIT",
        "role": "M365 seats (optional live)",
        "extra": "m365",
    },
    {
        "name": "Azure Identity",
        "package": "azure-identity",
        "license": "MIT",
        "role": "Graph auth (optional live)",
        "extra": "m365",
    },
    {
        "name": "Slack SDK",
        "package": "slack-sdk",
        "license": "MIT",
        "role": "Slack seats (optional live)",
        "extra": "slack",
    },
    {
        "name": "PyGithub",
        "package": "PyGithub",
        "license": "LGPL-3.0",
        "role": "GitHub seats (leaf dep, not vendored)",
        "extra": "github",
    },
    {
        "name": "Google API client",
        "package": "google-api-python-client",
        "license": "Apache-2.0",
        "role": "Workspace seats (optional live)",
        "extra": "google",
    },
)


def _pkg_version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _pip_audit() -> dict[str, Any]:
    binary = shutil.which("pip-audit")
    if not binary:
        return {"ran": False, "reason": "pip-audit not on PATH; OSV.dev scan skipped"}
    try:
        proc = subprocess.run(  # noqa: S603 — argv list, no shell
            [binary, "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ran": False, "reason": str(exc)}
    payload: Any
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"raw": (proc.stdout or "")[:2000]}
    return {"ran": True, "exit_code": proc.returncode, "osv": "osv.dev", "result": payload}


def inventory() -> Inventory:
    tools = []
    for item in OSS_INVENTORY:
        version = _pkg_version(item["package"])
        tools.append(
            ToolRecord(
                name=item["name"],
                package=item["package"],
                license=item["license"],
                role=item["role"],
                extra=item["extra"],
                on_path=version is not None or bool(shutil.which(item["package"])),
                version=version,
            )
        )
    return Inventory(
        version=__version__,
        modules=list(MODULES),
        tool_count=len(tools),
        tools=tools,
        pip_audit=_pip_audit(),
        gates={
            "trivy_pin": TRIVY_PIN,
            "trivy_refused": list(TRIVY_MALICIOUS),
            "graph_scopes": list(GRAPH_SCOPES),
            "metadata_only": True,
            "pygithub_vendored": False,
            "keepalive": "licensespend/state/keepalive.txt",
            "primary_oss": list(OSS_PRIMARY_TOOLS),
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
