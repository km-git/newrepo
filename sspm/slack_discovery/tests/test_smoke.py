"""Smoke tests for sspm.slack_discovery."""

from __future__ import annotations

from sspm.slack_discovery import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
