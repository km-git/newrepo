"""Unit tests for cost/report_writer."""

from __future__ import annotations

from cost.report_writer.service import run


def test_report_writer_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert "disclaimer" in result
