"""Pinned OSS inventory, licenses, and hard safety gates."""

from __future__ import annotations

from typing import Final

PRESIDIO_SOURCE: Final = "data-privacy-stack/presidio"
PRESIDIO_ANALYZER_PIN: Final = "2.2.360"
PRESIDIO_ANONYMIZER_PIN: Final = "2.2.360"
CNSPEC_PIN: Final = "13.37.0"
DUCKDB_PIN: Final = "1.5.5"

# Build #1 (SSPM) does not ship Trivy or Steampipe.
NO_TRIVY: Final = True
NO_STEAMPIPE: Final = True

DISALLOWED_AUTO_MERGE_PATHS: Final = (
    "sspm/disclaimers/",
    "sspm/loop/",
)

OSS_INVENTORY: Final = (
    {
        "name": "Mondoo cnspec",
        "package": "cnspec",
        "version": CNSPEC_PIN,
        "license": "MIT/Apache-2.0",
        "role": "SaaS configuration scan (ms365, google-workspace, github, slack, okta)",
        "module": "m365_discovery",
        "install": "CLI subprocess; brew tap mondoohq/mondoo && brew install cnspec",
        "last_update": "2026-09",
    },
    {
        "name": "pip-audit",
        "package": "pip-audit",
        "version": "2.9.0",
        "license": "Apache-2.0",
        "role": "Python supply-chain inventory",
        "module": "audit",
        "install": "pip pip-audit",
        "last_update": "2026-09",
    },
    {
        "name": "Mend Bolt for GitHub",
        "package": "mend-bolt-for-github",
        "version": "free-app",
        "license": "Marketplace (free)",
        "role": "PR dependency alerts",
        "module": "audit",
        "install": "GitHub App",
        "last_update": "2026-09",
    },
    {
        "name": "DuckDB",
        "package": "duckdb",
        "version": DUCKDB_PIN,
        "license": "MIT",
        "role": "in-process SQL drift diffs",
        "module": "config_drift",
        "install": "pip duckdb",
        "last_update": "2026-09",
    },
    {
        "name": "Microsoft Graph SDK",
        "package": "msgraph-sdk",
        "version": "1.5.0",
        "license": "MIT",
        "role": "M365 tenant + OAuth grant read",
        "module": "m365_discovery",
        "install": "pip msgraph-sdk (optional extra)",
        "last_update": "2026-09",
    },
    {
        "name": "Google API Python Client",
        "package": "google-api-python-client",
        "version": "2.165.0",
        "license": "Apache-2.0",
        "role": "Workspace Admin SDK + Reports API",
        "module": "google_workspace_discovery",
        "install": "pip google-api-python-client (optional extra)",
        "last_update": "2026-09",
    },
    {
        "name": "PyGithub",
        "package": "PyGithub",
        "version": "2.6.1",
        "license": "LGPL-3.0",
        "role": "GitHub org + OAuth app inventory",
        "module": "github_discovery",
        "install": "pip PyGithub",
        "last_update": "2026-09",
    },
    {
        "name": "slack-sdk",
        "package": "slack-sdk",
        "version": "3.36.0",
        "license": "MIT",
        "role": "Slack workspace admin settings (no message bodies)",
        "module": "slack_discovery",
        "install": "pip slack-sdk (optional extra)",
        "last_update": "2026-09",
    },
    {
        "name": "Presidio",
        "package": "presidio-analyzer",
        "version": PRESIDIO_ANALYZER_PIN,
        "license": "MIT",
        "role": "PII scrub of report output",
        "module": "report_writer",
        "install": f"pip from {PRESIDIO_SOURCE} (not microsoft/presidio)",
        "last_update": "2026-09",
    },
    {
        "name": "Jinja2",
        "package": "jinja2",
        "version": "3.1.5",
        "license": "BSD-3-Clause",
        "role": "Configuration & Inventory Report templates",
        "module": "report_writer",
        "install": "pip jinja2",
        "last_update": "2026-09",
    },
    {
        "name": "croniter",
        "package": "croniter",
        "version": "6.0.0",
        "license": "MIT",
        "role": "per-tenant scan schedule",
        "module": "multi_tenant",
        "install": "pip croniter",
        "last_update": "2026-09",
    },
    {
        "name": "httpx",
        "package": "httpx",
        "version": "0.28.1",
        "license": "BSD-3-Clause",
        "role": "forum-watcher + optional Graph/Okta REST",
        "module": "loop",
        "install": "pip httpx",
        "last_update": "2026-09",
    },
)
