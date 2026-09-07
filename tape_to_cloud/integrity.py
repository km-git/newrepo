"""SHA-256 of real file bytes. MD5 and SHA-1 are refused as primary hashes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

HASH_ALG = "SHA-256"
CHUNK = 1024 * 1024
REFUSED = ("MD5", "SHA-1", "SHA1")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_hex(digest: str) -> str:
    value = (digest or "").strip().lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"invalid sha256 digest: {digest!r}")
    return value


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "canonical_sha256"}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
