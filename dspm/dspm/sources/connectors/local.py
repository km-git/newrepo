"""Local filesystem + NFS (mounted) connector."""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from dspm.sources.connectors.base import BaseConnector
from dspm.sources.models import DataObject, ObjectPreview
from dspm.sources.uri import parse_uri

TEXT_EXTENSIONS = {
    ".csv",
    ".json",
    ".txt",
    ".xml",
    ".html",
    ".htm",
    ".md",
    ".log",
    ".eml",
    ".msg",
    ".pst",
    ".mbox",  # mail archives (PST needs special - list only)
    ".sql",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
}
ARCHIVE_EXTENSIONS = {".tar", ".gz", ".tgz", ".zip", ".bak", ".backup", ".dump"}
DATA_EXTENSIONS = TEXT_EXTENSIONS | ARCHIVE_EXTENSIONS | {".parquet", ".avro", ".orc", ".pdf", ".docx", ".xlsx"}


class LocalConnector(BaseConnector):
    provider = "local"

    def _resolve_path(self, uri: str) -> Path:
        _scheme, location = parse_uri(uri)
        p = Path(location)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p

    def discover(self, uri: str, max_objects: int = 500) -> list[DataObject]:
        root = self._resolve_path(uri)
        scheme, _ = parse_uri(uri)
        provider = "nfs" if scheme == "nfs" else "local"
        objects: list[DataObject] = []
        if not root.exists():
            return objects
        if root.is_file():
            return [self._file_object(uri, root, provider, "")]
        for item in sorted(root.rglob("*")):
            if len(objects) >= max_objects:
                break
            if not item.is_file():
                continue
            if item.suffix.lower() in DATA_EXTENSIONS or item.stat().st_size < 50_000_000:
                rel = str(item.relative_to(root))
                objects.append(self._file_object(uri, item, provider, rel))
        return objects

    def _file_object(self, uri: str, path: Path, provider: str, rel: str) -> DataObject:
        stat = path.stat()
        mime, _ = mimetypes.guess_type(str(path))
        store_type = "archive" if path.suffix.lower() in ARCHIVE_EXTENSIONS else "file"
        return DataObject(
            uri=uri,
            path=rel or path.name,
            name=path.name,
            provider=provider,
            store_type=store_type,
            size_bytes=stat.st_size,
            mime_type=mime,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            parent_uri=uri,
        )

    def preview(self, uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
        root = self._resolve_path(uri)
        target = root / path if path else root
        if not target.exists() or not target.is_file():
            return ObjectPreview(uri=uri, path=path, content_type="unknown", preview_text="", truncated=False)
        raw = target.read_bytes()[:max_bytes]
        truncated = target.stat().st_size > max_bytes
        try:
            text = raw.decode("utf-8")
            ctype = "text"
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
            ctype = "binary"
        return ObjectPreview(
            uri=uri,
            path=path or target.name,
            content_type=ctype,
            preview_text=text,
            truncated=truncated,
            size_bytes=target.stat().st_size,
        )
