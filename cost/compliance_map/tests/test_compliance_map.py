"""Unit tests for cost/compliance_map."""

from __future__ import annotations

from cost.compliance_map.service import run


def test_compliance_map_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["rows"]
