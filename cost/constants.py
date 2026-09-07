"""Build constants, OSS inventory, and report language guards."""

from __future__ import annotations

PRESIDIO_SOURCE = "data-privacy-stack/presidio"
TRIVY_PIN = "0.71.2"
TRIVY_MALICIOUS = frozenset({"0.69.4", "0.69.3", "0.69.2", "0.69.1", "0.69.0"})

FORBIDDEN_REPORT_WORDS = frozenset(
    {
        "compliance",
        "attestation",
        "certified",
        "secure",
        "guaranteed",
        "guarantees",
    }
)

ALLOWED_REPORT_PHRASES = (
    "cost observation",
    "configuration reference",
    "framework reference",
    "Cloud Cost & Configuration Review",
)

OSS_INVENTORY: list[dict[str, str]] = [
    {
        "tool": "Steampipe",
        "package": "steampipe",
        "license": "AGPL-3.0",
        "version": "2.4.4",
        "usage": "cli-subprocess-only",
    },
    {
        "tool": "Prowler",
        "package": "prowler",
        "license": "Apache-2.0",
        "version": "5.41.0",
        "usage": "cli-subprocess-only",
    },
    {
        "tool": "Cloud Custodian",
        "package": "c7n",
        "license": "Apache-2.0",
        "version": "0.9.45",
        "usage": "dryrun-default",
    },
    {"tool": "c7n-org", "package": "c7n-org", "license": "Apache-2.0", "version": "0.9.45", "usage": "multi-account"},
    {"tool": "DuckDB", "package": "duckdb", "license": "MIT", "version": "1.5.5", "usage": "analytics"},
    {"tool": "Presidio", "package": "presidio-analyzer", "license": "MIT", "version": "2.2.360", "usage": "pii-scrub"},
    {"tool": "Trivy", "package": "trivy", "license": "Apache-2.0", "version": TRIVY_PIN, "usage": "iac-scan"},
    {"tool": "pip-audit", "package": "pip-audit", "license": "Apache-2.0", "version": "2.9.0", "usage": "inventory"},
    {"tool": "boto3", "package": "boto3", "license": "Apache-2.0", "version": "1.35.0", "usage": "aws-apis"},
    {"tool": "Jinja2", "package": "jinja2", "license": "BSD-3-Clause", "version": "3.1.5", "usage": "report-templates"},
]

FRAMEWORKS = {
    "finops-foundation": "FinOps Foundation Framework",
    "aws-well-architected-cost": "AWS Well-Architected Cost Optimization",
    "azure-well-architected-cost": "Azure Well-Architected Cost Optimization",
    "gcp-architecture-cost": "GCP Architecture Framework Cost Optimization",
}
