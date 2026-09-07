"""Unit tests for cost/aws_inventory."""

from __future__ import annotations

from cost.aws_inventory.service import run


def test_aws_inventory_sandbox_runs() -> None:
    result = run(sandbox=True)
    assert result["provider"] == "aws"
    assert result["resources"]
