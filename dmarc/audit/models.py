"""Workspace + OSS tool inventory."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from dmarc import __version__


class ToolRecord(BaseModel):
    name: str
    version: str
    license: str
    last_update: str
    role: str
    primary: bool = False


class Inventory(BaseModel):
    generated_at: str
    toolkit_version: str = __version__
    tools: list[ToolRecord] = Field(default_factory=list)


def utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def installed_version(dist: str, fallback: str) -> str:
    try:
        from importlib.metadata import version

        return version(dist)
    except Exception:
        return fallback


def default_tools() -> list[ToolRecord]:
    today = utcnow()[:10]
    return [
        ToolRecord(
            name="pip-audit",
            version=installed_version("pip-audit", "2.9.0"),
            license="Apache-2.0",
            last_update=today,
            role="Python dependency advisory scan",
            primary=True,
        ),
        ToolRecord(
            name="dnspython",
            version=installed_version("dnspython", "2.7.0"),
            license="BSD-2-Clause",
            last_update=today,
            role="DNS record lookup",
            primary=True,
        ),
        ToolRecord(
            name="cryptography",
            version=installed_version("cryptography", "44.0.0"),
            license="Apache-2.0 OR BSD-3-Clause",
            last_update=today,
            role="DKIM public-key length",
            primary=True,
        ),
        ToolRecord(
            name="parsedmarc",
            version=installed_version("parsedmarc", "8.6.4"),
            license="MIT",
            last_update=today,
            role="Optional RUA/RUF parser (built-in XML parser is default)",
            primary=True,
        ),
        ToolRecord(
            name="duckdb",
            version=installed_version("duckdb", "1.5.5"),
            license="MIT",
            last_update=today,
            role="Optional SQL view over findings",
        ),
        ToolRecord(
            name="plotly",
            version=installed_version("plotly", "5.24.0"),
            license="MIT",
            last_update=today,
            role="Standalone HTML charts",
            primary=True,
        ),
        ToolRecord(
            name="presidio-analyzer",
            version=installed_version("presidio-analyzer", "2.2.360"),
            license="MIT",
            last_update=today,
            role="Optional forensic PII mask (data-privacy-stack/presidio)",
        ),
        ToolRecord(
            name="aiosmtplib",
            version=installed_version("aiosmtplib", "3.0.1"),
            license="MIT",
            last_update=today,
            role="Inbox-placement SMTP send",
        ),
        ToolRecord(
            name="jinja2",
            version=installed_version("jinja2", "3.1.5"),
            license="BSD-3-Clause",
            last_update=today,
            role="Markdown report templates",
        ),
        ToolRecord(
            name="ruff",
            version=installed_version("ruff", "0.9.4"),
            license="MIT",
            last_update=today,
            role="Lint / Bugbot replacement",
        ),
        ToolRecord(
            name="mend-bolt-for-github",
            version="GitHub App",
            license="Vendor free tier",
            last_update=today,
            role="GitHub App dependency scanning (operator-installed)",
            primary=True,
        ),
    ]


def build_inventory() -> dict[str, Any]:
    inv = Inventory(generated_at=utcnow(), tools=default_tools())
    return inv.model_dump()
