"""Smoke tests for sspm.report_writer."""

from __future__ import annotations

from sspm.report_writer import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
