"""Governance — Snowflake Horizon inspired masking + row access policies."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from dspm.store.db import fetch_all, init_db, insert_row

DEFAULT_MASKING_POLICIES = [
    {
        "name": "mp_pii_email",
        "policy_type": "masking",
        "framework": "horizon",
        "definition": {
            "column_types": ["EMAIL", "PII"],
            "mask": "hash",
            "roles_full_access": ["DATA_ADMIN", "DATA_GOVERNOR"],
        },
    },
    {
        "name": "mp_pci_partial",
        "policy_type": "masking",
        "framework": "horizon",
        "definition": {
            "column_types": ["PCI"],
            "mask": "partial_last4",
            "roles_full_access": ["DATA_ADMIN"],
        },
    },
    {
        "name": "rap_geo_restrict",
        "policy_type": "row_access",
        "framework": "horizon",
        "definition": {
            "column": "state",
            "allowed_roles": {"DATA_USER": ["MA"], "DATA_GOVERNOR": ["*"]},
        },
    },
]


def seed_policies() -> list[dict]:
    init_db()
    existing = fetch_all("governance_policies", limit=1)
    if existing:
        return fetch_all("governance_policies", limit=50)
    now = datetime.now(timezone.utc).isoformat()
    created = []
    for p in DEFAULT_MASKING_POLICIES:
        row = {
            "name": p["name"],
            "policy_type": p["policy_type"],
            "framework": p["framework"],
            "definition": json.dumps(p["definition"]),
            "created_at": now,
        }
        insert_row("governance_policies", row)
        created.append({**p, "created_at": now})
    return created


def apply_mask(value: str, data_type: str, role: str = "DATA_USER") -> str:
    policies = seed_policies()
    for p in policies:
        if p["policy_type"] != "masking":
            continue
        defn = p["definition"] if isinstance(p["definition"], dict) else json.loads(p["definition"])
        if data_type in defn.get("column_types", []):
            if role in defn.get("roles_full_access", []):
                return value
            mask = defn.get("mask", "hash")
            if mask == "hash":
                return "***masked***"
            if mask == "partial_last4" and len(value) >= 4:
                return "*" * (len(value) - 4) + value[-4:]
    return value


def list_policies() -> list[dict]:
    policies = fetch_all("governance_policies", limit=50)
    if not policies:
        return seed_policies()
    for p in policies:
        if isinstance(p.get("definition"), str):
            p["definition"] = json.loads(p["definition"])
    return policies
