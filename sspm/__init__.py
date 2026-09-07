"""SSPM-as-report: read-only SaaS configuration posture reports."""

__version__ = "0.1.0"

MODULES = (
    "audit",
    "m365_discovery",
    "google_workspace_discovery",
    "github_discovery",
    "slack_discovery",
    "okta_discovery",
    "oauth_grants",
    "config_drift",
    "compliance_map",
    "report_writer",
    "multi_tenant",
    "disclaimers",
)

OSS_PRIMARY_TOOLS = (
    "pip-audit",
    "mondoo-cnspec",
    "msgraph-sdk",
    "google-api-python-client",
    "PyGithub",
    "slack-sdk",
    "duckdb",
    "presidio",
    "jinja2",
)
