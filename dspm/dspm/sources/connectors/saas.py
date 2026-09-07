"""Generic SaaS connector — Google Drive, Dropbox, Box (metadata + fixture mode)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

from dspm.sources.connectors.base import BaseConnector
from dspm.sources.models import DataObject, ObjectPreview

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "saas_objects.json"


class SaasConnector(BaseConnector):
    provider = "saas"

    def _parse(self, uri: str) -> str:
        parsed = urlparse(uri)
        return parsed.netloc or parsed.path.split("/")[0] or "gdrive"

    def discover(self, uri: str, max_objects: int = 500) -> list[DataObject]:
        vendor = self._parse(uri)
        token = os.environ.get(f"SAAS_{vendor.upper()}_TOKEN") or os.environ.get("SAAS_API_TOKEN")
        if token and vendor == "gdrive":
            try:
                return self._discover_gdrive(token, uri, max_objects)
            except Exception:
                pass
        return self._fixture_objects(uri, vendor, max_objects)

    def _discover_gdrive(self, token: str, uri: str, limit: int) -> list[DataObject]:
        headers = {"Authorization": f"Bearer {token}"}
        objects: list[DataObject] = []
        with httpx.Client(timeout=30) as client:
            r = client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params={"pageSize": min(limit, 100), "fields": "files(id,name,mimeType,size,modifiedTime)"},
            )
            r.raise_for_status()
            for f in r.json().get("files", []):
                objects.append(
                    DataObject(
                        uri=uri,
                        path=f["id"],
                        name=f["name"],
                        provider="saas",
                        store_type=f.get("mimeType", "file"),
                        size_bytes=int(f.get("size", 0)) or None,
                        modified_at=f.get("modifiedTime"),
                        metadata={"vendor": "gdrive"},
                    )
                )
        return objects

    def _fixture_objects(self, uri: str, vendor: str, limit: int) -> list[DataObject]:
        if not FIXTURES.exists():
            return []
        data = json.loads(FIXTURES.read_text(encoding="utf-8"))
        items = data.get(vendor, data.get("objects", []))
        return [
            DataObject(
                uri=uri,
                path=item["path"],
                name=item["name"],
                provider="saas",
                store_type=item.get("store_type", "unstructured"),
                size_bytes=item.get("size"),
                metadata={"vendor": vendor, **item.get("metadata", {})},
            )
            for item in items[:limit]
        ]

    def preview(self, uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
        vendor = self._parse(uri)
        if FIXTURES.exists():
            data = json.loads(FIXTURES.read_text(encoding="utf-8"))
            for item in data.get(vendor, data.get("objects", [])):
                if item.get("path") == path:
                    text = item.get("preview", "")
                    return ObjectPreview(uri=uri, path=path, content_type="text", preview_text=text[:max_bytes])
        return ObjectPreview(uri=uri, path=path, content_type="unknown", preview_text="")
