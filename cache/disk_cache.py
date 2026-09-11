"""Compressed disk cache with deduplication for token-efficient agent operations.

Index is stdlib sqlite + JSON (no diskcache pickle). Blobs are zstd + msgpack.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, TypeVar

import msgpack
import pandas as pd
import zstandard as zstd

T = TypeVar("T")

DEFAULT_CACHE_DIR = Path(os.environ.get("EW_CACHE_DIR", ".cache/ew_tool"))
COMPRESS_LEVEL = 3
_DF_TAG = "__ew_df__"
_SERIES_TAG = "__ew_series__"
_NDARRAY_TAG = "__ew_ndarray__"


def _cache_key(namespace: str, *parts: Any) -> str:
  """Stable SHA-256 key from namespace + serialized parts."""
  payload = json.dumps([namespace, *parts], sort_keys=True, default=str)
  return hashlib.sha256(payload.encode()).hexdigest()


def _compress(data: bytes) -> bytes:
  return zstd.ZstdCompressor(level=COMPRESS_LEVEL).compress(data)


def _decompress(data: bytes) -> bytes:
  return zstd.ZstdDecompressor().decompress(data)


def _encode(obj: Any) -> Any:
  """Convert values to msgpack-safe types. DataFrames use JSON split, not pickle."""
  if isinstance(obj, pd.DataFrame):
    return {_DF_TAG: True, "json": obj.to_json(orient="split", date_format="iso")}
  if isinstance(obj, pd.Series):
    return {_SERIES_TAG: True, "json": obj.to_json(orient="split", date_format="iso")}
  if isinstance(obj, dict):
    return {str(k): _encode(v) for k, v in obj.items()}
  if isinstance(obj, tuple):
    return [_encode(v) for v in obj]
  if isinstance(obj, list):
    return [_encode(v) for v in obj]
  try:
    import numpy as np

    if isinstance(obj, np.ndarray):
      return {_NDARRAY_TAG: True, "dtype": str(obj.dtype), "shape": list(obj.shape), "data": obj.tolist()}
    if isinstance(obj, np.integer):
      return int(obj)
    if isinstance(obj, np.floating):
      return float(obj)
    if isinstance(obj, np.bool_):
      return bool(obj)
  except ImportError:
    pass
  return obj


def _decode(obj: Any) -> Any:
  if isinstance(obj, dict) and obj.get(_DF_TAG) is True:
    df = pd.read_json(io.StringIO(obj["json"]), orient="split")
    if len(df.index) and not isinstance(df.index, pd.DatetimeIndex):
      parsed = pd.to_datetime(df.index, utc=True, errors="coerce")
      if parsed.notna().all():
        df.index = parsed
    return df
  if isinstance(obj, dict) and obj.get(_SERIES_TAG) is True:
    return pd.read_json(io.StringIO(obj["json"]), orient="split", typ="series")
  if isinstance(obj, dict) and obj.get(_NDARRAY_TAG) is True:
    import numpy as np

    return np.array(obj["data"], dtype=obj.get("dtype")).reshape(obj.get("shape") or (-1,))
  if isinstance(obj, dict):
    return {k: _decode(v) for k, v in obj.items()}
  if isinstance(obj, list):
    return [_decode(v) for v in obj]
  return obj


def _dumps(value: Any) -> bytes:
  return msgpack.packb(_encode(value), use_bin_type=True)


def _loads(raw: bytes) -> Any:
  return _decode(msgpack.unpackb(raw, raw=False))


class _SqliteIndex:
  """TTL key/value index. JSON payloads only — no pickle."""

  def __init__(self, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    self._conn = sqlite3.connect(str(path), check_same_thread=False)
    self._conn.execute(
      "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, payload TEXT NOT NULL, expires REAL)"
    )
    self._conn.commit()

  def get(self, key: str) -> Optional[dict]:
    row = self._conn.execute("SELECT payload, expires FROM kv WHERE k=?", (key,)).fetchone()
    if row is None:
      return None
    payload, expires = row
    if expires is not None and float(expires) < time.time():
      self.delete(key)
      return None
    data = json.loads(payload)
    return data if isinstance(data, dict) else None

  def set(self, key: str, value: dict, expire: Optional[int] = None) -> None:
    expires = (time.time() + expire) if expire else None
    self._conn.execute(
      "INSERT OR REPLACE INTO kv (k, payload, expires) VALUES (?,?,?)",
      (key, json.dumps(value), expires),
    )
    self._conn.commit()

  def delete(self, key: str) -> None:
    self._conn.execute("DELETE FROM kv WHERE k=?", (key,))
    self._conn.commit()

  def __iter__(self) -> Iterator[str]:
    now = time.time()
    rows = self._conn.execute("SELECT k, expires FROM kv").fetchall()
    for key, expires in rows:
      if expires is not None and float(expires) < now:
        continue
      yield key

  def __len__(self) -> int:
    now = time.time()
    row = self._conn.execute(
      "SELECT COUNT(*) FROM kv WHERE expires IS NULL OR expires >= ?",
      (now,),
    ).fetchone()
    return int(row[0]) if row else 0


class CompressedCache:
  """
  Two-tier cache:
  - sqlite JSON index (fast metadata lookups, TTL)
  - zstd-compressed msgpack blobs on disk (compact payloads, no pickle)
  """

  def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, ttl: int = 3600):
    self.cache_dir = Path(cache_dir)
    self.cache_dir.mkdir(parents=True, exist_ok=True)
    self._index = _SqliteIndex(self.cache_dir / "index.sqlite")
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
    return _loads(raw)

  def set(self, namespace: str, value: Any, *key_parts: Any) -> str:
    key = _cache_key(namespace, *key_parts)
    packed = _dumps(value)
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
