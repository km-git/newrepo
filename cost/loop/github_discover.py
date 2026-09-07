"""GitHub repository discovery (search API or fixture). $0, unauthenticated optional."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cost.loop.watch import fetch_text

DEFAULT_QUERIES = (
    "topic:cost",
    "pii-detection language:Python stars:>40",
    "data-classification stars:>80",
)
SEARCH_URL = "https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=10"


def parse_search(payload: Any, *, query: str) -> list[dict[str, Any]]:
    items = payload.get("items") if isinstance(payload, dict) else payload
    found: list[dict[str, Any]] = []
    for row in items or []:
        license_info = row.get("license") or {}
        spdx = ""
        if isinstance(license_info, dict):
            spdx = str(license_info.get("spdx_id") or license_info.get("key") or "")
        html = str(row.get("html_url") or "")
        if not html:
            continue
        found.append(
            {
                "url": html,
                "title": str(row.get("full_name") or row.get("name") or html),
                "summary": str(row.get("description") or "")[:600],
                "source": f"github-search:{query}",
                "module_hint": _hint(row),
                "license": spdx,
                "category": "github_tool",
                "stars": int(row.get("stargazers_count") or 0),
            }
        )
    return found


def _hint(row: dict[str, Any]) -> str:
    blob = f"{row.get('full_name', '')} {row.get('description', '')} {' '.join(row.get('topics') or [])}".lower()
    if "pii" in blob or "presidio" in blob or "anonym" in blob:
        return "cost/classification"
    if "iam" in blob or "cartography" in blob or "privilege" in blob:
        return "cost/access"
    if "secret" in blob or "gitleaks" in blob or "iac" in blob:
        return "cost/encryption_check"
    if "cspm" in blob or "scout" in blob or "prowler" in blob:
        return "cost/exposure"
    return "cost/discovery"


def discover_github(
    *,
    fixture: str | Path | None = None,
    fetch: bool = False,
    queries: tuple[str, ...] = DEFAULT_QUERIES,
) -> list[dict[str, Any]]:
    if fixture:
        payload = json.loads(Path(fixture).read_text(encoding="utf-8"))
        query = "fixture"
        if isinstance(payload, dict) and "query" in payload:
            query = str(payload["query"])
            payload = payload.get("items") or payload
        return parse_search(payload if not isinstance(payload, list) else {"items": payload}, query=query)
    if not fetch:
        return []
    found: list[dict[str, Any]] = []
    for query in queries:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        body = fetch_text(url)
        found.extend(parse_search(json.loads(body), query=query))
    return found
