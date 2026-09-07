"""Shared paths, env flags, and Trivy pin."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"
PRICEBOOK = PKG / "usage" / "pricebook.yaml"
CONTRACTS = PKG / "renewals" / "contracts.yaml"
ALLOW_RECLAIM = PKG / "allow-reclaim.txt"
STATE_DIR = PKG / "state"
KEEPALIVE = STATE_DIR / "keepalive.txt"

SAMPLE_AS_OF = date(2026, 9, 7)
IDLE_THRESHOLDS = (30, 60, 90)
SAMPLE_CLIENTS = (
    {
        "id": "acme",
        "label": "Acme",
        "blurb": "12x Microsoft 365 E3 · Slack Business+ · GitHub Team",
    },
    {
        "id": "northwind",
        "label": "Northwind",
        "blurb": "20x Microsoft 365 E5 · denser unused seats for QBR sample",
    },
)
HONEST_GAPS = (
    "Graph last-signin lags; idle is unused, not never.",
    "Slack guests are unbilled; conversations.history is never called.",
    "GitHub last-active uses audit-log events when present; outside collaborators are unbilled.",
    "Pricebook is operator-edited AUD list prices, not a crawler.",
    "Shadow scan is SSO catalog + SPF includes + expense CSV, not a CASB.",
    "Draft reclaim pack only. Dual-gate reclaim records intent; no vendor mutate APIs.",
    "Annual seat contracts usually cannot drop quantity mid-term; right-size at the next renewal.",
    "Idle 30/60/90 is an operator policy, not a vendor definition of unused.",
)

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


def resolve_fixture_root(client: str, fixture_root: Path | None = None) -> Path:
    """Map explorer/report client ids to fixture directories.

    ``acme`` / ``fixture`` use the golden pack at ``examples/``. Named sample
    tenants live under ``examples/<client>/``.
    """
    if fixture_root is not None:
        return Path(fixture_root)
    key = (client or "fixture").strip().lower()
    if key in {"", "fixture", "acme"}:
        return EXAMPLES
    candidate = EXAMPLES / key
    if candidate.is_dir() and any((candidate / name).is_dir() for name in ("m365", "slack", "github", "shadow")):
        return candidate
    return EXAMPLES
