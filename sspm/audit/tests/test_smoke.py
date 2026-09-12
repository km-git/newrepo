"""Smoke tests for sspm.audit."""

from __future__ import annotations

from sspm.audit import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
