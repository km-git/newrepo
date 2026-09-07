"""Unit tests for cost/audit."""

from __future__ import annotations

from cost.audit.service import run


def test_audit_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["tool_count"] >= 8
