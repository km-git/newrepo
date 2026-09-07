"""Unit tests for cost/loop."""

from __future__ import annotations

from cost.loop.service import run


def test_loop_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["ok"] is True
