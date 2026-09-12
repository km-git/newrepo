"""Slack workspace discovery. No channel history or message content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore
from sspm.discovery import discover as discover_tenant


def discover_slack(
    *,
    workspace: str | None = None,
    admin_token_env: str = "SLACK_ADMIN_TOKEN",
    tenant_name: str = "slack-demo",
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    _ = (workspace, admin_token_env)
    return discover_tenant(
        "slack",
        tenant_name=tenant_name or (workspace or "slack-demo"),
        fixture=fixture,
        store=store,
    )
