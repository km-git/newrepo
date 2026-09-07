"""Audit module — workspace + OSS tool inventory."""

from __future__ import annotations

import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path

from dspm.models import OssToolInfo

MODULES = [
    "audit",
    "discovery",
    "classification",
    "risk",
    "access",
    "exposure",
    "encryption_check",
    "shadow",
    "custom_types",
    "compliance",
    "ai_security",
    "remediation",
    "catalog",
    "governance",
    "siem",
    "observability",
    "warehouse",
    "integrations",
    "sources",
    "web",
    "loop",
]

PRIMARY_OSS_TOOLS = [
    ("presidio-analyzer", "MIT", "classification"),
    ("duckdb", "MIT", "risk"),
    ("cloudquery", "Apache-2.0", "discovery"),
    ("prowler", "Apache-2.0", "exposure"),
    ("trivy", "Apache-2.0", "encryption_check"),
    ("steampipe", "AGPL-3.0", "access"),
    ("cloud-custodian", "Apache-2.0", "remediation"),
    ("datahub", "Apache-2.0", "audit"),
    ("openmetadata", "Apache-2.0", "catalog"),
    ("apache-polaris", "Apache-2.0", "catalog"),
    ("fastapi", "MIT", "web"),
]


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def build_inventory() -> dict:
    tools: list[dict] = []
    for name, license_, module in PRIMARY_OSS_TOOLS:
        tools.append(
            OssToolInfo(
                name=name,
                version=_pkg_version(name.replace("-", "_") if name == "cloud-custodian" else name),
                license=license_,
                module=module,
                last_update=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ).model_dump()
        )
    # Override known pip package names
    pip_map = {
        "presidio-analyzer": "presidio-analyzer",
        "duckdb": "duckdb",
        "cloudquery": "cloudquery",
        "prowler": "prowler",
        "trivy": "trivy",
        "steampipe": "steampipe",
        "cloud-custodian": "c7n",
        "datahub": "acryl-datahub",
        "openmetadata": "openmetadata-ingestion",
        "apache-polaris": "apache-polaris",
        "fastapi": "fastapi",
    }
    for i, (name, license_, module) in enumerate(PRIMARY_OSS_TOOLS):
        pip_name = pip_map.get(name, name)
        tools[i]["version"] = _pkg_version(pip_name)
        if tools[i]["version"] == "not-installed":
            tools[i]["version"] = "cli-subprocess"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "modules": MODULES,
        "oss_tools": tools,
        "module_count": len(MODULES),
        "oss_tool_count": len(PRIMARY_OSS_TOOLS),
    }


def ensure_schema(schema_path: Path | None = None) -> None:
    """Write schema marker; full Postgres init via docker-compose."""
    root = Path(__file__).resolve().parents[1]
    schema = schema_path or root / "db" / "schema.sql"
    if not schema.exists():
        raise FileNotFoundError(schema)


def write_inventory_json(out_path: Path) -> dict:
    inv = build_inventory()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(inv, indent=2), encoding="utf-8")
    return inv
