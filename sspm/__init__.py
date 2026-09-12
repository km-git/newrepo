"""SSPM-as-report: read-only SaaS configuration posture for M365, GWS, GitHub, Slack, Okta."""

from __future__ import annotations

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

TENANT_TYPES = ("m365", "gws", "github", "slack", "okta")

OSS_PRIMARY_TOOLS = (
    "cnspec",
    "pip-audit",
    "duckdb",
    "presidio",
    "msgraph-sdk",
    "google-api-python-client",
    "PyGithub",
    "slack-sdk",
)

# Reports must never claim these. Mapping tables may use "control reference".
FORBIDDEN_REPORT_WORDS = (
    "compliance",
    "attestation",
    "certified",
    "secure",
    "guaranteed",
    "guarantees",
)
