"""GitHub integrations — repo scanning, releases, security advisories."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
_GH_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe_name(value: str, kind: str) -> str:
    if not _GH_NAME.fullmatch(value or ""):
        raise ValueError(f"invalid GitHub {kind}")
    return value


def scan_repo(owner: str, repo: str, token: str | None = None) -> dict[str, Any]:
    owner = _safe_name(owner, "owner")
    repo = _safe_name(repo, "repo")
    token = token or os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    results: dict[str, Any] = {"owner": owner, "repo": repo, "findings": []}
    with httpx.Client(timeout=30) as client:
        # Dependabot alerts (requires auth)
        if token:
            r = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/dependabot/alerts", headers=headers)
            if r.status_code == 200:
                for alert in r.json()[:10]:
                    results["findings"].append(
                        {
                            "type": "dependency",
                            "severity": alert.get("security_advisory", {}).get("severity", "unknown"),
                            "package": alert.get("security_vulnerability", {}).get("package", {}).get("name"),
                            "cve": alert.get("security_advisory", {}).get("cve_id"),
                        }
                    )
        # Secret scanning (public repos may 404 without auth)
        r2 = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/secret-scanning/alerts", headers=headers)
        if r2.status_code == 200:
            for alert in r2.json()[:10]:
                results["findings"].append(
                    {
                        "type": "secret",
                        "severity": "high",
                        "secret_type": alert.get("secret_type"),
                        "state": alert.get("state"),
                    }
                )
        # Repo metadata
        r3 = client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers)
        if r3.status_code == 200:
            meta = r3.json()
            results["metadata"] = {
                "description": meta.get("description"),
                "language": meta.get("language"),
                "stars": meta.get("stargazers_count"),
                "private": meta.get("private"),
            }
    return results


def list_org_repos(org: str, token: str | None = None, limit: int = 10) -> list[dict]:
    org = _safe_name(org, "org")
    token = token or os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{GITHUB_API}/orgs/{org}/repos?per_page={limit}", headers=headers)
        if r.status_code != 200:
            return []
        return [{"name": x["name"], "full_name": x["full_name"], "private": x["private"]} for x in r.json()]
