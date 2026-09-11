"""Smoke tests for sspm.m365_discovery."""

from __future__ import annotations

from sspm.m365_discovery import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
