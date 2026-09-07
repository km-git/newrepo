"""DSPM-like-Cyera: 12-module open-source Data Security Posture Management."""

from __future__ import annotations

__version__ = "0.1.0"

MODULES = (
    "audit",
    "discovery",
    "classification",
    "risk",
    "access",
    "exposure",
    "encryption_check",
    "shadow",
    "custom_types",
    "compliance",
    "ai_security",
    "remediation",
)

OSS_PRIMARY_TOOLS = (
    "cloudquery",
    "presidio",
    "duckdb",
    "steampipe",
    "prowler",
    "trivy",
    "cloud-custodian",
    "datahub",
)
