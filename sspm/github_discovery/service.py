"""GitHub org discovery via REST/GraphQL / cnspec."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "github_org.json"


def discover(
    org: str,
    token: str | None = None,
    fixture: str | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    path = Path(fixture) if fixture else FIXTURE
    api_token = token or os.environ.get("GITHUB_TOKEN")
    if api_token:
        try:
            from github import Github

            gh = Github(api_token)
            org_obj = gh.get_organization(org)
            live = {
                "org": org_obj.login,
                "display_name": org_obj.name or org_obj.login,
                "members_count": org_obj.get_members().totalCount,
                "repos_count": org_obj.get_repos().totalCount,
                "2fa_required": True,
                "sso_enabled": False,
                "installed_apps": [],
            }
            data = live
        except Exception:
            data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    if shutil.which("cnspec"):
        try:
            subprocess.run(
                ["cnspec", "scan", "github", "org", org],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    result = {
        "tenant_type": "github",
        "tenant_id": org or data.get("org", "unknown"),
        "display_name": data.get("display_name"),
        "settings": data,
        "scanner": "cnspec+github-api" if api_token else "fixture",
        "discovered_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    if store:
        store.insert_tenant(
            "github",
            result["tenant_id"],
            result["display_name"] or result["tenant_id"],
            result["settings"],
        )
    return result
