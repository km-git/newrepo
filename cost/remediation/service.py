"""Cloud Custodian dry-run plans."""

from __future__ import annotations

from pathlib import Path

POLICIES_DIR = Path(__file__).with_name("policies")
MANUAL_REVIEW_PREFIX = "cost/remediation/policies/"


def should_block_auto_merge(changed_files: list[str]) -> bool:
    return any(MANUAL_REVIEW_PREFIX in name.replace("\\", "/") for name in changed_files)
