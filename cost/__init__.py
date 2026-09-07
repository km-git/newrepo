"""Cloud Cost & Configuration Review — read-only cost + config reports."""

__version__ = "0.1.0"

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
