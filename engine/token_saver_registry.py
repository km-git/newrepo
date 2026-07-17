"""Token-saver library registry — web-researched stack, auto-install, status."""

from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TokenSaverLib:
  name: str
  pip_spec: str
  import_name: str
  role: str
  source: str


# Curated from PyPI / GitHub web search (2026) — token counting, compression, cache
TOKEN_SAVER_LIBRARIES: Tuple[TokenSaverLib, ...] = (
  TokenSaverLib("tiktoken", "tiktoken>=0.7.0", "tiktoken", "accurate BPE token counts", "openai/tiktoken"),
  TokenSaverLib("diskcache", "diskcache>=5.6.0", "diskcache", "persistent SQLite disk cache", "grantjenks/python-diskcache"),
  TokenSaverLib("zstandard", "zstandard>=0.22.0", "zstandard", "zstd compression for cache blobs", "facebook/zstd"),
  TokenSaverLib("llm-token-optimizer", "llm-token-optimizer[tiktoken]>=1.0.0", "llm_token_optimizer", "prompt compress + cost estimate", "pypi/llm-token-optimizer"),
  TokenSaverLib("tokenpruner", "tokenpruner[tiktoken]>=1.0.0", "tokenpruner", "composite prompt pruning 70-80%", "pypi/tokenpruner"),
  TokenSaverLib("joblib", "joblib>=1.3.0", "joblib", "memoize expensive LLM calls to disk", "joblib/joblib"),
  TokenSaverLib("cachetic", "cachetic>=0.6.0", "cachetic", "typed pydantic cache + zstd", "allen2c/cachetic"),
  TokenSaverLib("foldback-ai", "foldback-ai>=0.1.0", "foldback", "lossless agent context compression", "pypi/foldback-ai"),
)


def _is_installed(import_name: str) -> bool:
  try:
    importlib.import_module(import_name)
    return True
  except ImportError:
    return False


def library_status() -> List[Dict[str, Any]]:
  rows = []
  for lib in TOKEN_SAVER_LIBRARIES:
    rows.append(
      {
        "name": lib.name,
        "pip_spec": lib.pip_spec,
        "role": lib.role,
        "source": lib.source,
        "installed": _is_installed(lib.import_name),
      }
    )
  return rows


def missing_libraries() -> List[TokenSaverLib]:
  return [lib for lib in TOKEN_SAVER_LIBRARIES if not _is_installed(lib.import_name)]


def install_missing_libraries(*, upgrade: bool = False) -> Dict[str, Any]:
  """pip install any token-saver libraries not yet importable."""
  missing = missing_libraries()
  if not missing:
    return {"installed": [], "skipped": [lib.name for lib in TOKEN_SAVER_LIBRARIES], "errors": []}

  specs = [lib.pip_spec for lib in missing]
  cmd = [sys.executable, "-m", "pip", "install"]
  if upgrade:
    cmd.append("--upgrade")
  cmd.extend(specs)

  proc = subprocess.run(cmd, capture_output=True, text=True)
  errors = []
  if proc.returncode != 0:
    errors.append(proc.stderr.strip() or proc.stdout.strip())

  still_missing = [lib.name for lib in missing_libraries()]
  installed = [lib.name for lib in missing if lib.name not in still_missing]
  return {
    "installed": installed,
    "still_missing": still_missing,
    "errors": errors,
    "pip_command": " ".join(cmd),
  }


def optimize_prompt_text(text: str) -> Tuple[str, Dict[str, Any]]:
  """
  Apply best available prompt optimizer (token-gated).
  Falls back to minified JSON / whitespace strip when libs absent.
  """
  meta: Dict[str, Any] = {"optimized": False, "library": None, "tokens_saved": 0}

  if _is_installed("llm_token_optimizer"):
    try:
      from llm_token_optimizer import optimize_prompt

      result = optimize_prompt(text, strategies=["whitespace", "fillers", "dedup"])
      saved = int(getattr(result, "tokens_saved", 0) or 0)
      if saved > 0:
        meta = {"optimized": True, "library": "llm-token-optimizer", "tokens_saved": saved}
        return result.optimized_text, meta
    except Exception:
      pass

  if _is_installed("tokenpruner"):
    try:
      from tokenpruner import PruningConfig, PruningStrategy, TextPruner

      pruner = TextPruner(PruningConfig(strategy=PruningStrategy.COMPOSITE, target_ratio=0.5))
      result = pruner.prune(text)
      saved = int(getattr(result, "tokens_saved", 0) or 0)
      if saved > 0:
        meta = {"optimized": True, "library": "tokenpruner", "tokens_saved": saved}
        return result.text, meta
    except Exception:
      pass

  # Built-in fallback: collapse whitespace
  collapsed = " ".join((text or "").split())
  if len(collapsed) < len(text or ""):
    meta = {"optimized": True, "library": "builtin", "tokens_saved": max(0, (len(text) - len(collapsed)) // 4)}
    return collapsed, meta

  return text, meta


def registry_summary() -> Dict[str, Any]:
  libs = library_status()
  return {
    "libraries": libs,
    "installed_count": sum(1 for l in libs if l["installed"]),
    "total_count": len(libs),
    "missing": [l["name"] for l in libs if not l["installed"]],
    "internal": ["cache/disk_cache", "cache/dedup", "cache/TokenStore", "core/consensus (GitHub EW)"],
  }
