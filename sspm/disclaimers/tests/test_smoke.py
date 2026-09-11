"""Smoke tests for sspm.disclaimers."""

from __future__ import annotations

from sspm.disclaimers import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
