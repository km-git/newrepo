"""Cloud Cost & Configuration Review — read-only cost + configuration reports."""

from __future__ import annotations

__version__ = "0.1.0"
__title__ = "Cloud Cost & Configuration Review"

MODULES = (
    "audit",
    "aws_inventory",
    "azure_inventory",
    "gcp_inventory",
    "cost_explorer",
    "rightsizing",
    "untagged",
    "config_drift",
    "compliance_map",
    "report_writer",
    "loop",
    "multi_account",
    "webui",
)

OSS_PRIMARY_TOOLS = (
    "steampipe",
    "prowler",
    "cloud-custodian",
    "c7n-org",
    "duckdb",
    "presidio",
    "trivy",
    "pip-audit",
)
