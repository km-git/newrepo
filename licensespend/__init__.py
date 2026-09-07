"""SaaS License & Spend: seat-waste report for AU MSP clients.

Metadata only. Never stores mail, Slack messages, GitHub issue text, or Drive files.
Never revokes a seat unless ``--apply`` and ``LICENSESPEND_APPLY=1`` and the user id
is in ``allow-reclaim.txt``.
"""

from __future__ import annotations

__version__ = "0.1.0"

MODULES = (
    "audit",
    "m365",
    "slack",
    "github",
    "usage",
    "shadow",
    "renewals",
    "report",
)

OSS_PRIMARY_TOOLS = (
    "msgraph-sdk",
    "slack-sdk",
    "PyGithub",
    "duckdb",
    "pip-audit",
    "jinja2",
)
