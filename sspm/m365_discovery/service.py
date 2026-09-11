"""Microsoft 365 tenant discovery via Graph or cnspec. Mailbox bodies are never read."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sspm.db.store import FindingsStore
from sspm.discovery import discover as discover_tenant


def discover_m365(
    *,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret_env: str = "M365_CLIENT_SECRET",
    tenant_name: str = "m365-demo",
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    live = None
    secret = os.environ.get(client_secret_env) if client_id and tenant_id else None
    if secret:
        live = {
            "external_id": tenant_id,
            "display_name": tenant_name,
            "scanner": "graph-stub",
            "honest_gap": "Live Graph walk is opt-in; this build enumerates subscribedSkus (free tier) when SDKs are present.",
            "settings": [],
            "note": "msgraph-sdk extra not invoked in CI; fixture used unless SSPM_LIVE=1",
        }
        if os.environ.get("SSPM_LIVE") == "1":
            live = _graph_subscribed_skus(tenant_id or "", client_id or "", secret)
    return discover_tenant(
        "m365",
        tenant_name=tenant_name,
        live=live if os.environ.get("SSPM_LIVE") == "1" else None,
        fixture=fixture,
        store=store,
    )


def _graph_subscribed_skus(tenant_id: str, client_id: str, secret: str) -> dict[str, Any]:
    """Read-only license utilisation via /v1.0/subscribedSkus (not beta cloudLicensing)."""
    try:
        import httpx
    except ImportError:
        return {"external_id": tenant_id, "scanner": "graph", "settings": [], "error": "httpx missing"}
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    with httpx.Client(timeout=20) as client:
        token_resp = client.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "client_credentials",
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        token_resp.raise_for_status()
        token = token_resp.json()["access_token"]
        skus = client.get(
            "https://graph.microsoft.com/v1.0/subscribedSkus",
            headers={"Authorization": f"Bearer {token}"},
        )
        skus.raise_for_status()
    items = skus.json().get("value") or []
    return {
        "external_id": tenant_id,
        "display_name": tenant_id,
        "scanner": "graph",
        "honest_gap": "subscribedSkus only on this live path; full CIS pack needs cnspec.",
        "licenses": items,
        "settings": [
            {
                "name": f"sku.{row.get('skuPartNumber', 'unknown')}.consumed",
                "value": str(row.get("consumedUnits") or 0),
                "source": "graph.subscribedSkus",
            }
            for row in items
        ],
    }
