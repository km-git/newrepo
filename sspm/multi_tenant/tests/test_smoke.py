"""Smoke tests for sspm.multi_tenant."""

from __future__ import annotations

from sspm.multi_tenant import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
