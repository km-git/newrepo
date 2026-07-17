"""Tests for environment auto-install."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import engine.setup_environment as se


def test_find_gh_prefers_which(monkeypatch):
  monkeypatch.setattr(se.shutil, "which", lambda _: "/usr/bin/gh")
  assert se.find_gh() == "/usr/bin/gh"


def test_clone_github_libs_skips_existing(tmp_path, monkeypatch):
  libs = tmp_path / "libs"
  (libs / "pyharmonics" / ".git").mkdir(parents=True)
  monkeypatch.setattr(se, "LIBS_DIR", libs)
  results = se.clone_github_libs()
  assert any(r["name"] == "pyharmonics" and r["action"] == "exists" for r in results)


def test_setup_environment_structure(monkeypatch):
  monkeypatch.setattr(se, "ensure_venv", lambda: {"created": False, "path": ".venv"})
  monkeypatch.setattr(se, "clone_github_libs", lambda: [])
  monkeypatch.setattr(se, "install_requirements", lambda: {"ok": True})
  monkeypatch.setattr(se, "install_editable_libs", lambda: {"ok": True})
  monkeypatch.setattr(se, "install_runtime_extras", lambda: {"ok": True})
  monkeypatch.setattr(se, "install_token_savers", lambda: {"install": {}})
  monkeypatch.setattr(se, "install_gh_cli", lambda: {"installed": True, "path": "/usr/bin/gh"})
  monkeypatch.setattr(se, "configure_gh_auth", lambda: {"configured": False})
  monkeypatch.setattr(
    se,
    "verify_imports",
    lambda: [{"module": "taew", "symbol": "wave2_fibonacci_check", "ok": True}],
  )
  monkeypatch.setattr(se, "find_gh", lambda: "/usr/bin/gh")
  monkeypatch.setattr(se, "venv_python", lambda: Path("/fake/python"))

  out = se.setup_environment()
  assert out["ok"] is True
  assert "steps" in out
  assert out["gh"] == "/usr/bin/gh"
