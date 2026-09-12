"""Smoke tests for sspm.google_workspace_discovery."""

from __future__ import annotations

from sspm.google_workspace_discovery import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
