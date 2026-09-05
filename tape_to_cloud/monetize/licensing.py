"""Per-asset license tagging persisted in a sidecar manifest.

Blueprint section 9 step 5: "License tagging (per-document, persisted in the
manifest)". Tags reference the migrated asset by id and by the SHA-256 of the
source sidecar manifest so the license record is bound to the chain of
custody, and are stored in an append-friendly, deterministically serialized
JSON manifest.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from ._audit import append_audit, utc_now, utc_now_iso

LICENSE_CLASSES = ("commercially-licensable", "restricted", "unknown")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

MANIFEST_FILENAME = "license_manifest.json"
MANIFEST_SCHEMA = "tape-to-cloud/license-manifest/v1"


class LicenseValidationError(ValueError):
    """Raised when a license tag fails validation."""


def _parse_utc(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise LicenseValidationError(f"{field_name} is not ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise LicenseValidationError(f"{field_name} must be timezone-aware: {value!r}")
    return parsed


@dataclass(frozen=True)
class LicenseTag:
    """A per-asset license record.

    ``license_id`` may be an SPDX identifier (e.g. ``CC-BY-4.0``) or a custom
    commercial-terms identifier. ``expires_at`` is an ISO-8601 UTC timestamp,
    or ``None`` for a perpetual term. ``source_manifest_sha256`` binds the tag
    to the migration sidecar manifest of the asset.
    """

    asset_id: str
    license_id: str
    license_class: str
    rights: tuple[str, ...]
    territory: str
    expires_at: str | None
    attribution_required: bool
    source_manifest_sha256: str
    licensor_id: str = "unknown"
    tagged_at: str = field(default_factory=utc_now_iso)

    def validate(self) -> "LicenseTag":
        if not self.asset_id or not str(self.asset_id).strip():
            raise LicenseValidationError("asset_id must be a non-empty string")
        if not self.license_id or not str(self.license_id).strip():
            raise LicenseValidationError("license_id must be a non-empty string")
        if self.license_class not in LICENSE_CLASSES:
            raise LicenseValidationError(
                f"license_class must be one of {LICENSE_CLASSES}, got {self.license_class!r}"
            )
        if not isinstance(self.rights, tuple) or any(
            not isinstance(r, str) or not r.strip() for r in self.rights
        ):
            raise LicenseValidationError("rights must be a tuple of non-empty strings")
        if self.license_class == "commercially-licensable" and not self.rights:
            raise LicenseValidationError(
                "commercially-licensable tags must grant at least one right"
            )
        if not self.territory or not str(self.territory).strip():
            raise LicenseValidationError("territory must be a non-empty string")
        if self.expires_at is not None:
            _parse_utc(self.expires_at, "expires_at")
        if not _SHA256_RE.match(self.source_manifest_sha256 or ""):
            raise LicenseValidationError(
                "source_manifest_sha256 must be 64 lowercase hex characters"
            )
        _parse_utc(self.tagged_at, "tagged_at")
        return self

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return _parse_utc(self.expires_at, "expires_at") <= (now or utc_now())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rights"] = list(self.rights)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LicenseTag":
        payload = dict(data)
        payload["rights"] = tuple(payload.get("rights", ()))
        return cls(**payload)


class LicenseStore:
    """Sidecar license manifest with deterministic, append-friendly writes."""

    def __init__(self, store_dir: Path | str) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store_dir / MANIFEST_FILENAME

    def load_tags(self) -> list[LicenseTag]:
        if not self.manifest_path.exists():
            return []
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return [LicenseTag.from_dict(item) for item in data.get("tags", [])]

    def add_tag(self, tag: LicenseTag, actor: str | None = None) -> LicenseTag:
        """Validate a tag, append it to the manifest, and audit the write."""
        tag.validate()
        tags = self.load_tags()
        tags.append(tag)
        self._write(tags)
        append_audit(
            self.store_dir,
            action="license.tag",
            detail={"asset_id": tag.asset_id, "license_id": tag.license_id,
                    "license_class": tag.license_class},
            actor=actor,
        )
        return tag

    def _write(self, tags: Iterable[LicenseTag]) -> None:
        ordered = sorted(tags, key=lambda t: (t.asset_id, t.license_id, t.tagged_at))
        doc = {"schema": MANIFEST_SCHEMA, "tags": [t.to_dict() for t in ordered]}
        serialized = json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        self.manifest_path.write_text(serialized, encoding="utf-8")

    def tags_for_asset(self, asset_id: str) -> list[LicenseTag]:
        return [t for t in self.load_tags() if t.asset_id == asset_id]

    def latest_tag_for_asset(self, asset_id: str) -> LicenseTag | None:
        tags = sorted(self.tags_for_asset(asset_id), key=lambda t: t.tagged_at)
        return tags[-1] if tags else None

    def query_by_class(self, license_class: str) -> list[LicenseTag]:
        """Return all tags of a given license class (e.g. "restricted")."""
        if license_class not in LICENSE_CLASSES:
            raise LicenseValidationError(
                f"license_class must be one of {LICENSE_CLASSES}, got {license_class!r}"
            )
        return [t for t in self.load_tags() if t.license_class == license_class]


__all__ = [
    "LICENSE_CLASSES",
    "LicenseTag",
    "LicenseStore",
    "LicenseValidationError",
    "MANIFEST_FILENAME",
]
