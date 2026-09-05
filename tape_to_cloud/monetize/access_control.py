"""Access-policy generation for licensed datasets.

Blueprint section 9 step 7: datasets are pushed "to a customer's training
bucket with an access policy that requires the customer to use their own KMS
key". Policies are cloud-agnostic dicts with an AWS-S3-style rendering, scope
access to the asset prefixes covered by the license, and embed the license id
and expiry as conditions. Policies can be revoked explicitly or lapse at the
license expiry.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from ._audit import append_audit, canonical_json, sha256_hex, utc_now, utc_now_iso
from .licensing import LicenseTag, _parse_utc

POLICY_SCHEMA = "tape-to-cloud/access-policy/v1"
POLICIES_FILENAME = "access_policies.json"


class AccessPolicyError(ValueError):
    """Raised when an access policy cannot be generated or mutated."""


def generate_access_policy(
    tag: LicenseTag,
    consumer_id: str,
    kms_key_id: str,
    asset_prefixes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a cloud-agnostic access-policy document for one license/consumer.

    Requires the consumer's own KMS key, scopes access to the asset prefixes
    covered by the license (defaulting to ``assets/<asset_id>/``), and embeds
    the license id and expiry as policy conditions.
    """
    tag.validate()
    if not consumer_id or not str(consumer_id).strip():
        raise AccessPolicyError("consumer_id is required")
    if not kms_key_id or not str(kms_key_id).strip():
        raise AccessPolicyError(
            "kms_key_id is required: access policies must require the "
            "customer's own KMS key (blueprint section 9)"
        )
    if tag.is_expired():
        raise AccessPolicyError(
            f"license {tag.license_id} for asset {tag.asset_id} expired at {tag.expires_at}"
        )
    prefixes = [str(p) for p in (asset_prefixes or [f"assets/{tag.asset_id}/"])]
    if not prefixes or any(not p.strip() for p in prefixes):
        raise AccessPolicyError("asset_prefixes must be non-empty strings")
    issued_at = utc_now_iso()
    policy: dict[str, Any] = {
        "schema": POLICY_SCHEMA,
        "asset_id": tag.asset_id,
        "license_id": tag.license_id,
        "consumer": {"customer_id": consumer_id, "kms_key_id": kms_key_id},
        "asset_prefixes": sorted(prefixes),
        "conditions": {
            "require_customer_kms_key": kms_key_id,
            "license_id": tag.license_id,
            "expires_at": tag.expires_at,
        },
        "issued_at": issued_at,
        "status": "active",
        "revoked_at": None,
        "revocation_reason": None,
    }
    policy["policy_id"] = sha256_hex(
        canonical_json(
            {
                "asset_id": tag.asset_id,
                "license_id": tag.license_id,
                "consumer_id": consumer_id,
                "issued_at": issued_at,
            }
        )
    )[:24]
    return policy


def render_aws_s3_policy(policy: dict[str, Any], bucket: str) -> dict[str, Any]:
    """Render the cloud-agnostic policy as an AWS-S3-style policy document."""
    if not bucket or not bucket.strip():
        raise AccessPolicyError("bucket is required for AWS rendering")
    kms_key_id = policy["consumer"]["kms_key_id"]
    statement: dict[str, Any] = {
        "Sid": f"TapeToCloudLicense{policy['policy_id']}",
        "Effect": "Allow",
        "Principal": {"AWS": policy["consumer"]["customer_id"]},
        "Action": ["s3:GetObject", "s3:GetObjectVersion"],
        "Resource": [
            f"arn:aws:s3:::{bucket}/{prefix}*" for prefix in policy["asset_prefixes"]
        ],
        "Condition": {
            "StringEquals": {
                "s3:x-amz-server-side-encryption": "aws:kms",
                "s3:x-amz-server-side-encryption-aws-kms-key-id": kms_key_id,
                "aws:PrincipalTag/tape-to-cloud-license-id": policy["license_id"],
            }
        },
    }
    expires_at = policy["conditions"].get("expires_at")
    if expires_at is not None:
        statement["Condition"]["DateLessThan"] = {"aws:CurrentTime": expires_at}
    return {"Version": "2012-10-17", "Statement": [statement]}


def is_policy_active(policy: dict[str, Any], now: datetime | None = None) -> bool:
    """A policy is active unless explicitly revoked or past its license expiry."""
    if policy.get("status") != "active":
        return False
    expires_at = policy.get("conditions", {}).get("expires_at")
    if expires_at is not None:
        if _parse_utc(expires_at, "expires_at") <= (now or utc_now()):
            return False
    return True


class PolicyStore:
    """Persists issued access policies and their revocation state."""

    def __init__(self, store_dir: Path | str) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.policies_path = self.store_dir / POLICIES_FILENAME

    def load_policies(self) -> list[dict[str, Any]]:
        if not self.policies_path.exists():
            return []
        return json.loads(self.policies_path.read_text(encoding="utf-8")).get(
            "policies", []
        )

    def _write(self, policies: list[dict[str, Any]]) -> None:
        ordered = sorted(policies, key=lambda p: (p["issued_at"], p["policy_id"]))
        doc = {"schema": POLICY_SCHEMA, "policies": ordered}
        self.policies_path.write_text(
            json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    def issue(
        self,
        tag: LicenseTag,
        consumer_id: str,
        kms_key_id: str,
        asset_prefixes: Sequence[str] | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        policy = generate_access_policy(tag, consumer_id, kms_key_id, asset_prefixes)
        policies = self.load_policies()
        policies.append(policy)
        self._write(policies)
        append_audit(
            self.store_dir,
            action="policy.issue",
            detail={
                "policy_id": policy["policy_id"],
                "license_id": policy["license_id"],
                "consumer_id": consumer_id,
            },
            actor=actor,
        )
        return policy

    def get(self, policy_id: str) -> dict[str, Any] | None:
        for policy in self.load_policies():
            if policy["policy_id"] == policy_id:
                return policy
        return None

    def revoke(
        self, policy_id: str, reason: str = "explicit", actor: str | None = None
    ) -> dict[str, Any]:
        policies = self.load_policies()
        for policy in policies:
            if policy["policy_id"] == policy_id:
                if policy["status"] == "revoked":
                    raise AccessPolicyError(f"policy {policy_id} is already revoked")
                policy["status"] = "revoked"
                policy["revoked_at"] = utc_now_iso()
                policy["revocation_reason"] = reason
                self._write(policies)
                append_audit(
                    self.store_dir,
                    action="policy.revoke",
                    detail={"policy_id": policy_id, "reason": reason},
                    actor=actor,
                )
                return policy
        raise AccessPolicyError(f"policy {policy_id} not found")


__all__ = [
    "AccessPolicyError",
    "PolicyStore",
    "generate_access_policy",
    "is_policy_active",
    "render_aws_s3_policy",
]
