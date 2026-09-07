"""SHA-256 integrity manifests with optional HMAC signature."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_VERSION = "1.0"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _signing_key() -> bytes | None:
    raw = os.environ.get("EW_TTC_MANIFEST_KEY", "").strip()
    if not raw:
        return None
    return raw.encode("utf-8")


def sign_manifest(payload: Mapping[str, Any]) -> str | None:
    key = _signing_key()
    if key is None:
        return None
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def verify_manifest_signature(manifest: Mapping[str, Any]) -> bool:
    signature = manifest.get("signature")
    if not signature:
        return _signing_key() is None
    key = _signing_key()
    if key is None:
        return False
    body = {k: v for k, v in manifest.items() if k != "signature"}
    expected = sign_manifest(body)
    return expected == signature and hmac.compare_digest(expected, signature)


def build_file_manifest(
    files: Sequence[Path],
    *,
    job_id: str,
    module: str,
    root: Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for file_path in sorted(files, key=lambda p: str(p)):
        if not file_path.is_file():
            continue
        rel = str(file_path.relative_to(root)) if root and file_path.is_relative_to(root) else str(file_path)
        entries.append(
            {
                "path": rel,
                "size_bytes": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
        )
    manifest: dict[str, Any] = {
        "version": MANIFEST_VERSION,
        "job_id": job_id,
        "module": module,
        "created_at": datetime.now(UTC).isoformat(),
        "file_count": len(entries),
        "files": entries,
        "metadata": dict(metadata or {}),
    }
    sig = sign_manifest(manifest)
    if sig:
        manifest["signature"] = sig
    return manifest


def save_manifest(manifest: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not verify_manifest_signature(data):
        raise ValueError(f"manifest signature invalid: {path}")
    return data
