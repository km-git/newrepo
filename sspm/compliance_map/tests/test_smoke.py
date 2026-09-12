"""Smoke tests for sspm.compliance_map."""

from __future__ import annotations

from sspm.compliance_map import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
