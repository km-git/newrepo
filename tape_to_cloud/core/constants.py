"""Shared constants for the tape-to-cloud platform."""

from __future__ import annotations

MODULES: tuple[str, ...] = (
    "audit",
    "analytics",
    "vtl-cloud",
    "restore",
    "disk-ingest",
    "email-extract",
    "email-migrate",
    "tape-duplicate",
    "media-ingest",
    "tape-ops",
    "tape-saas",
    "tape-vault",
    "destroy",
    "llm-corpus",
    "ml-enrich",
    "monetize",
)

CROSS_CUTTING_LAYERS: tuple[str, ...] = (
    "integrity",
    "ediscovery",
    "kms-kmip",
    "worm",
    "format-readers",
    "media-rescue",
)

JOB_STATUSES: tuple[str, ...] = ("pending", "running", "completed", "failed", "cancelled")

DEFAULT_DATA_DIR = "output/tape_to_cloud"
