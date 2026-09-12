"""Local vault storage with optional S3-compatible backend stub."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .manifests import sha256_file


class VaultStorage:
    """Filesystem vault under ``<data_dir>/vault``."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.vault_root = data_dir / "vault"
        self.manifests_dir = data_dir / "manifests"
        self.vault_root.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def store_file(
        self,
        source: Path,
        *,
        namespace: str = "default",
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not source.is_file():
            raise FileNotFoundError(source)
        object_id = uuid4().hex
        dest_dir = self.vault_root / namespace / object_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name
        shutil.copy2(source, dest)
        digest = sha256_file(dest)
        record = {
            "object_id": object_id,
            "namespace": namespace,
            "name": source.name,
            "vault_path": str(dest.relative_to(self.data_dir)),
            "size_bytes": dest.stat().st_size,
            "sha256": digest,
            "stored_at": datetime.now(UTC).isoformat(),
            "metadata": dict(metadata or {}),
        }
        meta_path = dest_dir / "meta.json"
        meta_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    def get_object(self, object_id: str, namespace: str | None = "default") -> dict[str, Any] | None:
        if namespace:
            meta_path = self.vault_root / namespace / object_id / "meta.json"
            if meta_path.is_file():
                return json.loads(meta_path.read_text(encoding="utf-8"))
        for obj in self.list_objects():
            if obj.get("object_id") == object_id:
                return obj
        return None

    def list_objects(self, namespace: str | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        roots = [self.vault_root / namespace] if namespace else [p for p in self.vault_root.iterdir() if p.is_dir()]
        if namespace:
            roots = [self.vault_root / namespace]
        elif not self.vault_root.is_dir():
            return results
        for ns_dir in roots if namespace else list(self.vault_root.iterdir()):
            if not ns_dir.is_dir():
                continue
            for obj_dir in ns_dir.iterdir():
                meta = obj_dir / "meta.json"
                if meta.is_file():
                    results.append(json.loads(meta.read_text(encoding="utf-8")))
        return sorted(results, key=lambda r: r.get("stored_at", ""), reverse=True)

    def delete_object(self, object_id: str, namespace: str = "default", *, secure: bool = False) -> bool:
        obj_dir = self.vault_root / namespace / object_id
        if not obj_dir.is_dir():
            return False
        if secure:
            for fp in obj_dir.rglob("*"):
                if fp.is_file():
                    fp.write_bytes(b"\x00" * min(fp.stat().st_size, 4096))
        shutil.rmtree(obj_dir, ignore_errors=True)
        return True

    def resolve_path(self, record: Mapping[str, Any]) -> Path:
        return self.data_dir / record["vault_path"]


class S3BackendStub:
    """Optional S3 adapter — uses boto3 when installed."""

    def __init__(self, bucket: str, endpoint_url: str | None = None) -> None:
        self.bucket = bucket
        self.endpoint_url = endpoint_url

    def is_available(self) -> bool:
        try:
            import boto3  # noqa: F401
        except ImportError:
            return False
        return True

    def upload(self, local_path: Path, key: str) -> dict[str, Any]:
        if not self.is_available():
            return {"status": "skipped", "reason": "boto3 not installed", "key": key}
        import boto3

        client = boto3.client("s3", endpoint_url=self.endpoint_url)
        client.upload_file(str(local_path), self.bucket, key)
        return {"status": "uploaded", "bucket": self.bucket, "key": key}
