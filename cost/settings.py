"""Runtime settings. Live cloud APIs are opt-in; sandbox is the default."""

from __future__ import annotations

import os


def sandbox_mode() -> bool:
    raw = os.environ.get("COST_SANDBOX", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def database_url() -> str:
    return os.environ.get("COST_DATABASE_URL", "").strip()


def postgres_dsn() -> str:
    return os.environ.get(
        "COST_POSTGRES",
        "postgresql://cost:cost@127.0.0.1:5432/cost",
    )


def aws_profile() -> str:
    return os.environ.get("AWS_PROFILE", os.environ.get("COST_AWS_PROFILE", "")).strip()


def trivy_min_version() -> str:
    return "0.70.0"


def trivy_pinned_version() -> str:
    return os.environ.get("COST_TRIVY_VERSION", "0.71.2")
