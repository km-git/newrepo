"""Smoke tests for sspm.github_discovery."""

from __future__ import annotations

from sspm.github_discovery import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
