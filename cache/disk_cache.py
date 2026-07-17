"""Compressed disk cache with deduplication for token-efficient agent operations."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

import zstandard as zstd
from diskcache import Cache

T = TypeVar("T")

DEFAULT_CACHE_DIR = Path(os.environ.get("EW_CACHE_DIR", ".cache/ew_tool"))
COMPRESS_LEVEL = 3


def _cache_key(namespace: str, *parts: Any) -> str:
    """Stable SHA-256 key from namespace + serialized parts."""
    payload = json.dumps([namespace, *parts], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _compress(data: bytes) -> bytes:
    return zstd.ZstdCompressor(level=COMPRESS_LEVEL).compress(data)


def _decompress(data: bytes) -> bytes:
    return zstd.ZstdDecompressor().decompress(data)


class CompressedCache:
  """
  Two-tier cache:
  - diskcache index (fast metadata lookups, TTL)
  - zstd-compressed pickle blobs on disk (compact payloads)
  """

  def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, ttl: int = 3600):
    self.cache_dir = Path(cache_dir)
    self.cache_dir.mkdir(parents=True, exist_ok=True)
    self._index = Cache(str(self.cache_dir / "index"))
    self._blob_dir = self.cache_dir / "blobs"
    self._blob_dir.mkdir(exist_ok=True)
    self.ttl = ttl

  def get(self, namespace: str, *key_parts: Any) -> Optional[Any]:
    key = _cache_key(namespace, *key_parts)
    entry = self._index.get(key)
    if entry is None:
      return None
    blob_path = self._blob_dir / f"{key}.zst"
    if not blob_path.exists():
      return None
    raw = _decompress(blob_path.read_bytes())
    return pickle.loads(raw)

  def set(self, namespace: str, value: Any, *key_parts: Any) -> str:
    key = _cache_key(namespace, *key_parts)
    packed = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    blob_path = self._blob_dir / f"{key}.zst"
    blob_path.write_bytes(_compress(packed))
    self._index.set(key, {"namespace": namespace, "size": len(packed)}, expire=self.ttl)
    return key

  def get_or_compute(
    self,
    namespace: str,
    compute_fn: Callable[[], T],
    *key_parts: Any,
  ) -> tuple[T, bool]:
    """Return (value, cache_hit)."""
    cached = self.get(namespace, *key_parts)
    if cached is not None:
      return cached, True
    result = compute_fn()
    self.set(namespace, result, *key_parts)
    return result, False

  def invalidate_namespace(self, namespace: str) -> int:
    removed = 0
    for key in list(self._index):
      entry = self._index.get(key)
      if entry and entry.get("namespace") == namespace:
        self._index.delete(key)
        blob = self._blob_dir / f"{key}.zst"
        if blob.exists():
          blob.unlink()
          removed += 1
    return removed

  def stats(self) -> dict:
    blob_bytes = sum(f.stat().st_size for f in self._blob_dir.glob("*.zst"))
    return {
      "entries": len(self._index),
      "blob_bytes": blob_bytes,
      "blob_mb": round(blob_bytes / 1_048_576, 3),
      "cache_dir": str(self.cache_dir),
    }


# Module-level singleton for pipeline reuse across batch instruments
_global_cache: Optional[CompressedCache] = None
_llm_cache: Optional[CompressedCache] = None


def get_cache() -> CompressedCache:
  global _global_cache
  if _global_cache is None:
    _global_cache = CompressedCache()
  return _global_cache


def get_llm_cache() -> CompressedCache:
  """LLM advisory cache — longer TTL, structure-keyed (see llm_token_saver)."""
  global _llm_cache
  if _llm_cache is None:
    from engine.llm_token_saver import llm_cache_ttl

    _llm_cache = CompressedCache(ttl=llm_cache_ttl())
  return _llm_cache
