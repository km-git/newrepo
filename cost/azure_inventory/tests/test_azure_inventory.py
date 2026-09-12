"""Unit tests for cost/azure_inventory."""

from __future__ import annotations

from cost.azure_inventory.service import run


def test_azure_inventory_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["provider"] == "azure"
