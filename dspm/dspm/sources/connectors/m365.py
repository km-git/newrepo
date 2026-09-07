"""Microsoft 365 connector — SharePoint, OneDrive, Exchange via Graph API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

from dspm.sources.connectors.base import BaseConnector
from dspm.sources.models import DataObject, ObjectPreview

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "m365_graph.json"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class M365Connector(BaseConnector):
    provider = "m365"

    def _token(self) -> str | None:
        tenant = os.environ.get("AZURE_TENANT_ID")
        client_id = os.environ.get("AZURE_CLIENT_ID")
        secret = os.environ.get("AZURE_CLIENT_SECRET")
        if not all([tenant, client_id, secret]):
            return None
        url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "client_secret": secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        try:
            r = httpx.post(url, data=data, timeout=30)
            r.raise_for_status()
            return r.json().get("access_token")
        except Exception:
            return None

    def _parse(self, uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        # m365://sharepoint/sites/hr or m365://onedrive or m365://exchange
        service = parsed.netloc or "sharepoint"
        path = parsed.path.lstrip("/")
        return service, path

    def discover(self, uri: str, max_objects: int = 500) -> list[DataObject]:
        token = self._token()
        service, path = self._parse(uri)
        if token:
            try:
                objects = self._discover_graph(token, service, path, max_objects)
                if objects:
                    return objects
            except Exception:
                pass  # Graph unavailable; fall back to fixtures
        return self._fixture_objects(uri, service, max_objects)

    def _discover_graph(self, token: str, service: str, path: str, limit: int) -> list[DataObject]:
        headers = {"Authorization": f"Bearer {token}"}
        objects: list[DataObject] = []
        with httpx.Client(timeout=30) as client:
            if service == "sharepoint":
                r = client.get(f"{GRAPH_BASE}/sites?search=*", headers=headers)
                r.raise_for_status()
                for site in r.json().get("value", [])[:5]:
                    site_id = site["id"]
                    dr = client.get(f"{GRAPH_BASE}/sites/{site_id}/drives", headers=headers)
                    for drive in dr.json().get("value", []):
                        items = client.get(
                            f"{GRAPH_BASE}/drives/{drive['id']}/root/children",
                            headers=headers,
                        )
                        for item in items.json().get("value", [])[:limit]:
                            if "file" in item:
                                objects.append(
                                    DataObject(
                                        uri="m365://sharepoint",
                                        path=item.get("webUrl", item["name"]),
                                        name=item["name"],
                                        provider="m365",
                                        store_type="sharepoint_file",
                                        size_bytes=item.get("size"),
                                        metadata={"service": "sharepoint", "site": site.get("displayName")},
                                    )
                                )
            elif service == "onedrive":
                r = client.get(f"{GRAPH_BASE}/me/drive/root/children", headers=headers)
                for item in r.json().get("value", [])[:limit]:
                    if "file" in item:
                        objects.append(
                            DataObject(
                                uri="m365://onedrive",
                                path=item["name"],
                                name=item["name"],
                                provider="m365",
                                store_type="onedrive_file",
                                size_bytes=item.get("size"),
                            )
                        )
            elif service == "exchange":
                r = client.get(f"{GRAPH_BASE}/users?$top=10", headers=headers)
                for user in r.json().get("value", [])[:3]:
                    mr = client.get(
                        f"{GRAPH_BASE}/users/{user['id']}/messages?$top=20&$select=subject,bodyPreview",
                        headers=headers,
                    )
                    for msg in mr.json().get("value", [])[:limit]:
                        objects.append(
                            DataObject(
                                uri="m365://exchange",
                                path=msg.get("id", ""),
                                name=msg.get("subject", "message")[:80],
                                provider="m365",
                                store_type="mailbox_message",
                                metadata={"user": user.get("mail"), "preview": msg.get("bodyPreview", "")[:200]},
                            )
                        )
        return objects[:limit]

    def _fixture_objects(self, uri: str, service: str, limit: int) -> list[DataObject]:
        if not FIXTURES.exists():
            return []
        data = json.loads(FIXTURES.read_text(encoding="utf-8"))
        items = data.get(service, data.get("objects", []))
        return [
            DataObject(
                uri=uri,
                path=item["path"],
                name=item["name"],
                provider="m365",
                store_type=item.get("store_type", "unstructured"),
                size_bytes=item.get("size"),
                metadata=item.get("metadata", {}),
            )
            for item in items[:limit]
        ]

    def preview(self, uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
        if FIXTURES.exists():
            data = json.loads(FIXTURES.read_text(encoding="utf-8"))
            for svc_items in [data.get("sharepoint", []), data.get("onedrive", []), data.get("exchange", [])]:
                for item in svc_items:
                    if item.get("path") == path or item.get("name") == path:
                        text = item.get("preview", item.get("metadata", {}).get("preview", ""))
                        return ObjectPreview(
                            uri=uri, path=path, content_type="text",
                            preview_text=str(text)[:max_bytes], truncated=len(str(text)) > max_bytes,
                        )
        return ObjectPreview(uri=uri, path=path, content_type="unknown", preview_text="")
