"""SHA-256 of real file bytes. MD5 and SHA-1 are refused as primary hashes."""

from __future__ import annotations

import hashlib
import json
import re
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


SHA256_HEX_RE = re.compile(r"^([0-9a-f]{64})$")


def sha256_hex(digest: str) -> str:
    match = SHA256_HEX_RE.fullmatch((digest or "").strip().lower())
    if match is None:
        raise ValueError(f"invalid sha256 digest: {digest!r}")
    return match.group(1)


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "canonical_sha256"}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
