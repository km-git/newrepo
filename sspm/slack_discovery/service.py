"""Slack workspace discovery via admin API."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "slack_workspace.json"


def discover(
    workspace: str,
    admin_token: str | None = None,
    fixture: str | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    path = Path(fixture) if fixture else FIXTURE
    data = json.loads(path.read_text(encoding="utf-8"))
    if admin_token:
        try:
            from slack_sdk import WebClient

            client = WebClient(token=admin_token)
            info = client.team_info()
            team = info.get("team", {})
            data = {
                "workspace": team.get("domain", workspace),
                "display_name": team.get("name", workspace),
                "members_count": data.get("members_count", 0),
                "sso_enabled": data.get("sso_enabled", False),
                "message_retention_days": data.get("message_retention_days", 0),
                "installed_apps_count": data.get("installed_apps_count", 0),
            }
        except Exception:
            pass
    result = {
        "tenant_type": "slack",
        "tenant_id": workspace or data.get("workspace", "unknown"),
        "display_name": data.get("display_name"),
        "settings": data,
        "scanner": "slack-sdk" if admin_token else "fixture",
        "discovered_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    if store:
        store.insert_tenant(
            "slack",
            result["tenant_id"],
            result["display_name"] or result["tenant_id"],
            result["settings"],
        )
    return result
