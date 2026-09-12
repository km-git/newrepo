"""Smoke tests for sspm.config_drift."""

from __future__ import annotations

from sspm.config_drift import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
