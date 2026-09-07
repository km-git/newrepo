"""Content-addressed local object store (on-prem stand-in for SeaweedFS)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from tape_to_cloud.integrity import sha256_file, sha256_hex
from tape_to_cloud.worm import assert_unlocked

_DEFAULT_STORE = Path("output/tape_to_cloud/store")


def default_store() -> Path:
    return Path(os.environ.get("EW_TAPE_STORE", str(_DEFAULT_STORE)))


def object_path(store: Path, digest: str) -> Path:
    digest = sha256_hex(digest)
    dest = (store.resolve() / "objects" / digest[:2] / digest).resolve()
    dest.relative_to((store.resolve() / "objects").resolve())
    return dest


def put_file(store: Path, source: Path, *, expected_sha256: str | None = None) -> tuple[str, Path]:
    digest = sha256_file(source)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(f"pre-hash mismatch: {expected_sha256} != {digest}")
    dest = object_path(store, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(source, dest)
    post = sha256_file(dest)
    if post != digest:
        dest.unlink(missing_ok=True)
        raise ValueError(f"post-copy SHA-256 mismatch: {digest} != {post}")
    return digest, dest


def get_file(store: Path, digest: str, dest: Path) -> Path:
    src = object_path(store, digest)
    if not src.is_file():
        raise FileNotFoundError(digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    if sha256_file(dest) != digest:
        dest.unlink(missing_ok=True)
        raise ValueError("restore SHA-256 mismatch")
    return dest


def delete_object(store: Path, digest: str, job_dir: Path) -> None:
    assert_unlocked(job_dir)
    path = object_path(store, digest)
    if path.is_file():
        os.unlink(path)


__all__ = ["default_store", "delete_object", "get_file", "object_path", "put_file"]
