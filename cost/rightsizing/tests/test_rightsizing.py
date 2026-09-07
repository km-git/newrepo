"""Unit tests for cost/rightsizing."""

from __future__ import annotations

from cost.rightsizing.service import run


def test_rightsizing_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["findings"]
