"""Monetization Strategy Services (`monetize`).

Optional broker layer on top of migrated/cataloged assets: per-asset license
tagging, access-policy generation for licensed datasets, and royalty
reporting. Every mutating operation appends to an append-only audit log in
the store directory (blueprint sections 5, 9, and 12).
"""

from .access_control import (
    AccessPolicyError,
    PolicyStore,
    generate_access_policy,
    is_policy_active,
    render_aws_s3_policy,
)
from .licensing import (
    LICENSE_CLASSES,
    LicenseStore,
    LicenseTag,
    LicenseValidationError,
)
from .royalties import (
    RATE_MODELS,
    RateCard,
    RoyaltyError,
    UsageLedger,
    compute_royalty_report,
    render_report_summary,
)

__all__ = [
    "AccessPolicyError",
    "LICENSE_CLASSES",
    "LicenseStore",
    "LicenseTag",
    "LicenseValidationError",
    "PolicyStore",
    "RATE_MODELS",
    "RateCard",
    "RoyaltyError",
    "UsageLedger",
    "compute_royalty_report",
    "generate_access_policy",
    "is_policy_active",
    "render_aws_s3_policy",
    "render_report_summary",
]
