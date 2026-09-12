"""PyPI package discovery for catalog python_lib entries (JSON API or fixture)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cost.loop.gap_audit import load_catalog
from cost.loop.watch import fetch_text

PYPI_JSON = "https://pypi.org/pypi/{name}/json"


def parse_project(payload: dict[str, Any], *, pypi_name: str, module: str) -> dict[str, Any] | None:
    info = payload.get("info") or payload
    name = str(info.get("name") or pypi_name)
    version = str(info.get("version") or "")
    summary = str(info.get("summary") or "")[:600]
    license_name = str(info.get("license") or info.get("license_expression") or "")
    home = str(info.get("home_page") or info.get("project_url") or f"https://pypi.org/project/{name}/")
    if not version:
        return None
    return {
        "url": home or f"https://pypi.org/project/{name}/{version}/",
        "title": f"{name} {version} on PyPI",
        "summary": summary or f"PyPI release {name}=={version}",
        "source": "pypi",
        "module_hint": module,
        "license": license_name,
        "category": "python_lib",
        "pypi": name,
        "version": version,
    }


def discover_pypi(
    *,
    fixture: str | Path | None = None,
    fetch: bool = False,
    catalog_path: Path | None = None,
) -> list[dict[str, Any]]:
    if fixture:
        payload = json.loads(Path(fixture).read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("projects") or [payload]
        found = []
        for row in rows:
            info = row.get("info") or row
            name = str(info.get("name") or row.get("pypi") or "unknown")
            parsed = parse_project(
                row if "info" in row else {"info": row},
                pypi_name=name,
                module=str(row.get("module") or "cost/classification"),
            )
            if parsed:
                found.append(parsed)
        return found
    if not fetch:
        return []
    found = []
    for item in load_catalog(catalog_path):
        if item.get("category") != "python_lib" or not item.get("pypi"):
            continue
        name = str(item["pypi"])
        body = fetch_text(PYPI_JSON.format(name=name))
        parsed = parse_project(json.loads(body), pypi_name=name, module=str(item.get("module") or "cost/audit"))
        if parsed:
            found.append(parsed)
    return found
