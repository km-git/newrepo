"""Unit tests for cost/multi_account."""

from __future__ import annotations

from cost.multi_account.service import run


def test_multi_account_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["accounts"]
