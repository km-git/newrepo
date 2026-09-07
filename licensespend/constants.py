"""Shared paths, env flags, and Trivy pin."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"
PRICEBOOK = PKG / "usage" / "pricebook.yaml"
CONTRACTS = PKG / "renewals" / "contracts.yaml"
ALLOW_RECLAIM = PKG / "allow-reclaim.txt"
STATE_DIR = PKG / "state"
KEEPALIVE = STATE_DIR / "keepalive.txt"

ENV_INCLUDE_EMAIL = "LICENSESPEND_INCLUDE_EMAIL"
ENV_APPLY = "LICENSESPEND_APPLY"
ENV_SALT = "LICENSESPEND_SALT"
DEFAULT_SALT = "licensespend-dev"

TRIVY_PIN = "v0.71.2"
TRIVY_MALICIOUS = ("v0.69.4", "v0.69.5", "v0.69.6")

COMMERCIAL_SKIP = ("zylo", "productiv", "torii")

GRAPH_SCOPES = (
    "Organization.Read.All",
    "User.Read.All",
    "Directory.Read.All",
    "AuditLog.Read.All",
)


def include_email() -> bool:
    return os.environ.get(ENV_INCLUDE_EMAIL, "0") == "1"


def apply_enabled() -> bool:
    return os.environ.get(ENV_APPLY, "0") == "1"


def tenant_salt() -> str:
    return os.environ.get(ENV_SALT, DEFAULT_SALT)
