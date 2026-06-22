"""ElliottWaveAnalyzer import patch — fixes absolute `from models.X` imports."""

from __future__ import annotations

import sys
from pathlib import Path

_EWA_ROOT = Path(__file__).resolve().parent / "ElliottWaveAnalyzer"


def patch_ewa_imports() -> bool:
  """Add EWA root to sys.path and register models alias. Returns True if OK."""
  root = str(_EWA_ROOT)
  if root not in sys.path:
    sys.path.insert(0, root)
  try:
    import models  # noqa: F401
    return True
  except ImportError:
    return False


def verify_ewa() -> str:
  if not _EWA_ROOT.exists():
    return "missing"
  if patch_ewa_imports():
    try:
      from models.MonoWave import MonoWaveUp  # noqa: F401

      return "ok"
    except ImportError as e:
      return f"import_error:{e}"
  return "patch_failed"
