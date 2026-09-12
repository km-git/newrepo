"""Unit tests for cost/gcp_inventory."""

from __future__ import annotations

from cost.gcp_inventory.service import run


def test_gcp_inventory_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["provider"] == "gcp"
