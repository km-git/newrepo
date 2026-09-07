"""SSPM build constants and OSS inventory."""

from __future__ import annotations

from typing import Any

PRESIDIO_SOURCE = "data-privacy-stack/presidio"

FORBIDDEN_REPORT_WORDS = frozenset({"compliance", "attestation", "certified", "secure", "guaranteed", "guarantees"})

OSS_INVENTORY: list[dict[str, Any]] = [
    {
        "name": "pip-audit",
        "package": "pip-audit",
        "version": "2.9.0",
        "license": "Apache-2.0",
        "role": "dependency vulnerability inventory",
    },
    {
        "name": "mondoo-cnspec",
        "package": "mondoo-cnspec",
        "version": "13.37.0",
        "license": "MIT/Apache-2.0",
        "role": "SaaS posture scan engine (subprocess)",
    },
    {
        "name": "msgraph-sdk",
        "package": "msgraph-sdk",
        "version": "1.5.0",
        "license": "MIT",
        "role": "Microsoft 365 Graph API",
    },
    {
        "name": "google-api-python-client",
        "package": "google-api-python-client",
        "version": "2.165.0",
        "license": "Apache-2.0",
        "role": "Google Workspace Admin SDK",
    },
    {
        "name": "PyGithub",
        "package": "PyGithub",
        "version": "2.6.1",
        "license": "LGPL-3.0",
        "role": "GitHub org discovery",
    },
    {
        "name": "slack-sdk",
        "package": "slack-sdk",
        "version": "3.36.0",
        "license": "MIT",
        "role": "Slack workspace discovery",
    },
    {
        "name": "duckdb",
        "package": "duckdb",
        "version": "1.5.5",
        "license": "MIT",
        "role": "config drift SQL analytics",
    },
    {
        "name": "presidio-analyzer",
        "package": "presidio-analyzer",
        "version": "2.2.360",
        "license": "MIT",
        "role": "PII scrubbing for report output",
    },
    {
        "name": "jinja2",
        "package": "jinja2",
        "version": "3.1.5",
        "license": "BSD-3-Clause",
        "role": "report templates",
    },
]
