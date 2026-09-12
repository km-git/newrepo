"""End-to-end sandbox (or live) pipeline used by `make cost-all`."""

from __future__ import annotations

from typing import Any

from cost.audit import service as audit
from cost.aws_inventory import service as aws_inventory
from cost.azure_inventory import service as azure_inventory
from cost.compliance_map import service as compliance_map
from cost.config_drift import service as config_drift
from cost.cost_explorer import service as cost_explorer
from cost.gcp_inventory import service as gcp_inventory
from cost.loop import service as loop
from cost.multi_account import service as multi_account
from cost.report_writer import service as report_writer
from cost.rightsizing import service as rightsizing
from cost.untagged import service as untagged


def run_all(*, sandbox: bool = True, provider: str = "all", since: str = "30d") -> dict[str, Any]:
    inventory = audit.run(sandbox=sandbox)
    aws = aws_inventory.run(sandbox=sandbox)
    azure = azure_inventory.run(sandbox=sandbox)
    gcp = gcp_inventory.run(sandbox=sandbox)
    costs = cost_explorer.run(sandbox=sandbox, provider=provider, since=since)
    size = rightsizing.run(sandbox=sandbox, provider=provider)
    tags = untagged.run(sandbox=sandbox, provider=provider)
    drift = config_drift.run(sandbox=sandbox, provider=provider)
    framework = compliance_map.run(sandbox=sandbox, framework="finops-foundation")
    accounts = multi_account.run(sandbox=sandbox)
    report = report_writer.run(sandbox=sandbox, provider=provider, since=since)
    monthly = loop.monthly_rollup()
    return {
        "inventory": inventory,
        "aws": aws,
        "azure": azure,
        "gcp": gcp,
        "costs": costs,
        "rightsizing": size,
        "untagged": tags,
        "drift": drift,
        "framework": framework,
        "multi_account": accounts,
        "report": report,
        "monthly": monthly,
        "ok": True,
    }
