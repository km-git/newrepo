"""GitHub org discovery via REST/GraphQL or cnspec. Third-party apps = count + names."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore
from sspm.discovery import discover as discover_tenant


def discover_github(
    *,
    org: str | None = None,
    token_env: str = "GITHUB_TOKEN",
    tenant_name: str = "github-demo",
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    live = None
    token = os.environ.get(token_env) or os.environ.get("GH_TOKEN")
    if org and token and os.environ.get("SSPM_LIVE") == "1":
        live = _live_org(org, token)
    return discover_tenant(
        "github",
        tenant_name=tenant_name or (org or "github-demo"),
        live=live,
        fixture=fixture,
        store=store,
    )


def _live_org(org: str, token: str) -> dict[str, Any]:
    try:
        from github import Github
    except ImportError:
        return {"external_id": org, "scanner": "api", "settings": [], "error": "PyGithub missing"}
    gh = Github(token)
    organization = gh.get_organization(org)
    settings = [
        {
            "name": "two_factor_requirement.enabled",
            "value": str(bool(organization.two_factor_requirement_enabled)).lower(),
            "source": "github.org",
        },
        {
            "name": "default_repository_permission",
            "value": str(organization.default_repository_permission),
            "source": "github.org",
        },
        {
            "name": "members_can_create_public_repositories",
            "value": str(bool(organization.members_can_create_public_repos)).lower(),
            "source": "github.org",
        },
    ]
    apps = []
    try:
        installs = organization.get_installations()
        apps = [{"name": inst.app.name, "publisher": "github-app"} for inst in list(installs)[:50]]
    except Exception:
        apps = [{"name": "(count unavailable)", "publisher": "unknown"}]
    return {
        "external_id": org,
        "display_name": organization.login,
        "scanner": "api",
        "honest_gap": "Only first-party org settings; third-party app installations are count + names.",
        "apps": apps,
        "settings": settings,
    }
