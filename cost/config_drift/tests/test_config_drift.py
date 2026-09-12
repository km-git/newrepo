"""Unit tests for cost/config_drift."""

from __future__ import annotations

from cost.config_drift.service import run


def test_config_drift_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["findings"]
