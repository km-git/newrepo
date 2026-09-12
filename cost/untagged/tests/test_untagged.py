"""Unit tests for cost/untagged."""

from __future__ import annotations

from cost.untagged.service import run


def test_untagged_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["findings"]
