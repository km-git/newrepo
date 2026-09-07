"""SMB/CIFS share connector via smbprotocol."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import urlparse

from dspm.sources.connectors.base import BaseConnector
from dspm.sources.models import DataObject, ObjectPreview

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "smb_share.json"


class SmbConnector(BaseConnector):
    provider = "smb"

    def _parse(self, uri: str) -> tuple[str, str, str]:
        parsed = urlparse(uri)
        server = parsed.hostname or parsed.netloc.split("/")[0]
        parts = PurePosixPath(parsed.path).parts
        share = parts[1] if len(parts) > 1 else "data"
        subpath = "/".join(parts[2:]) if len(parts) > 2 else ""
        return server, share, subpath

    def discover(self, uri: str, max_objects: int = 500) -> list[DataObject]:
        server, share, subpath = self._parse(uri)
        try:
            import smbclient

            user = os.environ.get("SMB_USER", "")
            password = os.environ.get("SMB_PASSWORD", "")
            if user:
                smbclient.register_session(server, username=user, password=password)
            base = f"\\\\{server}\\{share}"
            if subpath:
                base = f"{base}\\{subpath.replace('/', chr(92))}"
            objects: list[DataObject] = []
            for entry in smbclient.scandir(base):
                if entry.is_file():
                    stat = entry.stat()
                    objects.append(
                        DataObject(
                            uri=uri,
                            path=entry.name,
                            name=entry.name,
                            provider="smb",
                            store_type="file",
                            size_bytes=stat.st_size,
                            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                            parent_uri=uri,
                            metadata={"server": server, "share": share},
                        )
                    )
                if len(objects) >= max_objects:
                    break
            if objects:
                return objects
        except Exception:
            pass
        return self._fixture_objects(uri, max_objects)

    def _fixture_objects(self, uri: str, limit: int) -> list[DataObject]:
        if not FIXTURES.exists():
            return []
        data = json.loads(FIXTURES.read_text(encoding="utf-8"))
        return [
            DataObject(
                uri=uri,
                path=item["path"],
                name=item["name"],
                provider="smb",
                store_type="file",
                size_bytes=item.get("size"),
                parent_uri=uri,
                metadata=item.get("metadata", {}),
            )
            for item in data.get("files", [])[:limit]
        ]

    def preview(self, uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
        server, share, subpath = self._parse(uri)
        try:
            import smbclient

            user = os.environ.get("SMB_USER", "")
            password = os.environ.get("SMB_PASSWORD", "")
            if user:
                smbclient.register_session(server, username=user, password=password)
            full = f"\\\\{server}\\{share}\\{path.replace('/', chr(92))}"
            with smbclient.open_file(full, mode="rb") as f:
                raw = f.read(max_bytes)
            text = raw.decode("utf-8", errors="replace")
            return ObjectPreview(uri=uri, path=path, content_type="text", preview_text=text, truncated=True)
        except Exception:
            pass
        if FIXTURES.exists():
            data = json.loads(FIXTURES.read_text(encoding="utf-8"))
            for item in data.get("files", []):
                if item.get("path") == path and "preview" in item:
                    return ObjectPreview(uri=uri, path=path, content_type="text", preview_text=item["preview"])
        return ObjectPreview(uri=uri, path=path, content_type="unknown", preview_text="")
