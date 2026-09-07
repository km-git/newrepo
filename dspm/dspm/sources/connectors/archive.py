"""Backup and archive connector — tar, zip, gzip, common backup extensions."""

from __future__ import annotations

import io
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from dspm.sources.connectors.base import BaseConnector
from dspm.sources.connectors.local import LocalConnector
from dspm.sources.models import DataObject, ObjectPreview
from dspm.sources.uri import parse_uri

BACKUP_EXTENSIONS = {".tar", ".tgz", ".gz", ".zip", ".bak", ".backup", ".dump", ".img", ".vhd"}


class ArchiveConnector(BaseConnector):
    provider = "backup"

    def _resolve_path(self, uri: str) -> Path:
        _, location = parse_uri(uri)
        p = Path(location)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p

    def discover(self, uri: str, max_objects: int = 500) -> list[DataObject]:
        path = self._resolve_path(uri)
        objects: list[DataObject] = []
        if path.is_dir():
            local = LocalConnector()
            for obj in local.discover(uri, max_objects=max_objects):
                if Path(obj.name).suffix.lower() in BACKUP_EXTENSIONS:
                    obj.provider = "backup"
                    obj.store_type = "archive"
                    objects.append(obj)
                    nested = self._list_archive_members(uri, path / obj.path, max_objects - len(objects))
                    objects.extend(nested)
            return objects[:max_objects]
        if path.is_file():
            objects.append(
                DataObject(
                    uri=uri,
                    path=path.name,
                    name=path.name,
                    provider="backup",
                    store_type="archive",
                    size_bytes=path.stat().st_size,
                    parent_uri=uri,
                )
            )
            objects.extend(self._list_archive_members(uri, path, max_objects - 1))
        return objects[:max_objects]

    def _list_archive_members(self, uri: str, path: Path, limit: int) -> list[DataObject]:
        members: list[DataObject] = []
        if not path.exists():
            return members
        try:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path) as zf:
                    for info in zf.infolist()[:limit]:
                        if info.is_dir():
                            continue
                        members.append(
                            DataObject(
                                uri=uri,
                                path=f"{path.name}!{info.filename}",
                                name=info.filename,
                                provider="backup",
                                store_type="archive_member",
                                size_bytes=info.file_size,
                                modified_at=datetime(*info.date_time, tzinfo=timezone.utc).isoformat(),
                                parent_uri=uri,
                                metadata={"archive": path.name, "compressed_size": info.compress_size},
                            )
                        )
            elif tarfile.is_tarfile(path):
                with tarfile.open(path) as tf:
                    for member in tf.getmembers()[:limit]:
                        if not member.isfile():
                            continue
                        members.append(
                            DataObject(
                                uri=uri,
                                path=f"{path.name}!{member.name}",
                                name=member.name,
                                provider="backup",
                                store_type="archive_member",
                                size_bytes=member.size,
                                modified_at=datetime.fromtimestamp(member.mtime, tz=timezone.utc).isoformat(),
                                parent_uri=uri,
                                metadata={"archive": path.name},
                            )
                        )
        except (OSError, zipfile.BadZipFile, tarfile.TarError):
            pass
        return members[:limit]

    def preview(self, uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
        if "!" in path:
            archive_name, member_path = path.split("!", 1)
            _, location = parse_uri(uri)
            archive_path = self._resolve_path(uri)
            if archive_path.is_dir():
                archive_path = archive_path / archive_name
            return self._preview_member(archive_path, member_path, uri, path, max_bytes)
        local = LocalConnector()
        return local.preview(uri, path, max_bytes)

    def _preview_member(
        self, archive_path: Path, member_path: str, uri: str, full_path: str, max_bytes: int
    ) -> ObjectPreview:
        try:
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path) as zf:
                    raw = zf.read(member_path)[:max_bytes]
            elif tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path) as tf:
                    f = tf.extractfile(member_path)
                    raw = (f.read(max_bytes) if f else b"")[:max_bytes]
            else:
                return ObjectPreview(uri=uri, path=full_path, content_type="unknown", preview_text="")
            text = raw.decode("utf-8", errors="replace")
            return ObjectPreview(
                uri=uri, path=full_path, content_type="text", preview_text=text, truncated=len(raw) >= max_bytes
            )
        except Exception:
            return ObjectPreview(uri=uri, path=full_path, content_type="error", preview_text="")
