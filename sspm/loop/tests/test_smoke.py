"""Smoke tests for sspm.loop."""

from __future__ import annotations

from sspm.loop import classify, issue_fix, monthly, watch


def test_module_imports() -> None:
    assert watch is not None
    assert classify is not None
    assert monthly is not None
    assert issue_fix is not None
