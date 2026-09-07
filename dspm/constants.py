"""Pinned OSS inventory, licenses, and hard safety gates."""

from __future__ import annotations

from typing import Final

PRESIDIO_SOURCE: Final = "data-privacy-stack/presidio"
PRESIDIO_ANALYZER_PIN: Final = "2.2.360"
PRESIDIO_ANONYMIZER_PIN: Final = "2.2.360"

TRIVY_PIN: Final = "0.71.2"
TRIVY_MIN: Final = (0, 70, 0)
TRIVY_MALICIOUS: Final = frozenset({"0.69.4", "0.69.5", "0.69.6"})

STEAMPIPE_PIN: Final = "2.4.4"
STEAMPIPE_LICENSE: Final = "AGPL-3.0"

RISK_WEIGHTS: Final = {
    "pii": 30,
    "public_exposure": 25,
    "overprivileged": 20,
    "unencrypted": 15,
    "custom": 10,
    "blast_radius_bonus": 20,
}

FINDING_TYPES: Final = ("PII", "PHI", "PCI", "secret", "IP", "custom")
VERDICTS: Final = ("PII", "sensitive", "public", "internal")

# CLI tools are subprocess-only. None of these are imported as Python libraries.
CLI_TOOLS: Final = ("cloudquery", "prowler", "steampipe", "trivy", "c7n")

OSS_INVENTORY: Final = (
    {
        "name": "CloudQuery",
        "package": "cloudquery",
        "version": "28.x",
        "license": "Apache-2.0",
        "role": "agentless data-store inventory",
        "module": "discovery",
        "install": "CLI (not pip); plugin-destination-postgresql v8.x",
        "last_update": "2026-09",
    },
    {
        "name": "Microsoft Presidio",
        "package": "presidio-analyzer",
        "version": PRESIDIO_ANALYZER_PIN,
        "license": "MIT",
        "role": "PII/PHI classification + anonymizer",
        "module": "classification",
        "install": f"pip from {PRESIDIO_SOURCE} (not microsoft/presidio)",
        "last_update": "2026-09",
    },
    {
        "name": "DuckDB",
        "package": "duckdb",
        "version": "1.5.5",
        "license": "MIT",
        "role": "in-process SQL risk scoring",
        "module": "risk",
        "install": "pip duckdb",
        "last_update": "2026-09",
    },
    {
        "name": "Steampipe",
        "package": "steampipe",
        "version": STEAMPIPE_PIN,
        "license": STEAMPIPE_LICENSE,
        "role": "SQL over cloud APIs (CLI subprocess only)",
        "module": "access",
        "install": "CLI subprocess; do not import as a library",
        "last_update": "2026-09",
    },
    {
        "name": "Prowler",
        "package": "prowler",
        "version": "5.41.0",
        "license": "Apache-2.0",
        "role": "public-exposure + CIS/compliance checks",
        "module": "exposure",
        "install": "pip prowler or CLI",
        "last_update": "2026-09",
    },
    {
        "name": "Trivy",
        "package": "trivy",
        "version": TRIVY_PIN,
        "license": "Apache-2.0",
        "role": "IaC + image + secret encryption/exposure scan",
        "module": "encryption_check",
        "install": f"CLI {TRIVY_PIN} (refuse {sorted(TRIVY_MALICIOUS)} / CVE-2026-33634)",
        "last_update": "2026-09",
    },
    {
        "name": "Cloud Custodian",
        "package": "c7n",
        "version": "0.9.45",
        "license": "Apache-2.0",
        "role": "policy-as-code remediation",
        "module": "remediation",
        "install": "pip c7n; policies require manual review before apply",
        "last_update": "2026-09",
    },
    {
        "name": "DataHub",
        "package": "datahub",
        "version": "1.2.0",
        "license": "Apache-2.0",
        "role": "metadata catalog (docker-compose profile)",
        "module": "audit",
        "install": "docker compose --profile catalog",
        "last_update": "2026-09",
    },
)
