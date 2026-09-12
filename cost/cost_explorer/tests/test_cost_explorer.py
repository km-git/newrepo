"""Unit tests for cost/cost_explorer."""

from __future__ import annotations

from cost.cost_explorer.service import run


def test_cost_explorer_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["rows"]
