"""Six cross-cutting layers required on every module."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .manifests import build_file_manifest, save_manifest


def apply_integrity(
    *,
    job_id: str,
    module: str,
    files: Sequence[Path],
    root: Path | None,
    manifests_dir: Path,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = build_file_manifest(files, job_id=job_id, module=module, root=root, metadata=metadata)
    path = manifests_dir / f"{job_id}-integrity.json"
    save_manifest(manifest, path)
    return {"layer": "integrity", "manifest_path": str(path), "file_count": manifest["file_count"]}


def apply_ediscovery(
    *,
    custodians: Sequence[str] | None = None,
    keywords: Sequence[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    legal_holds: Sequence[str] | None = None,
) -> dict[str, Any]:
    return {
        "layer": "ediscovery",
        "custodians": list(custodians or []),
        "keywords": list(keywords or []),
        "date_from": date_from,
        "date_to": date_to,
        "legal_holds": list(legal_holds or []),
        "defensibility_log": f"ediscovery-filter-{datetime.now(UTC).isoformat()}",
        "production_formats": ["pst", "nsf", "load_file"],
    }


def apply_kms_kmip(*, key_id: str | None = None, encrypt: bool = False) -> dict[str, Any]:
    resolved = key_id or os.environ.get("EW_TTC_KMIP_KEY_ID", "").strip()
    if encrypt and not resolved:
        raise PermissionError("kms-kmip: key missing — refuse read/encrypt")
    return {
        "layer": "kms-kmip",
        "key_id": resolved or None,
        "algorithm": "AES-256-GCM",
        "envelope_encrypted": encrypt and bool(resolved),
    }


def apply_worm(
    *,
    retention_days: int | None = None,
    mode: str = "governance",
    erasure_requested: bool = False,
) -> dict[str, Any]:
    if erasure_requested and retention_days:
        return {
            "layer": "worm",
            "action": "stop-and-ask",
            "reason": "WORM retention conflicts with right-to-erasure",
            "retention_days": retention_days,
            "mode": mode,
        }
    return {
        "layer": "worm",
        "action": "apply",
        "retention_days": retention_days,
        "mode": mode,
        "backends": ["s3_object_lock", "gcs_bucket_lock", "azure_immutable_blob", "tape_retention_lock"],
    }


def apply_format_readers(*, format_name: str | None = None) -> dict[str, Any]:
    plugins = {
        "tsm": "ibm_spectrum_protect",
        "netbackup": "cohesity_netbackup",
        "backup_exec": "arctera_backup_exec",
        "arcserve": "arcserve",
        "networker": "dell_networker",
        "data_protector": "hpe_data_protector",
        "commvault": "commvault",
        "veeam": "veeam_mtf",
        "dpx": "catalogic_dpx",
        "tar": "posix_tar",
        "ltfs": "ltfs",
    }
    key = (format_name or "unknown").lower().replace(" ", "_")
    plugin = plugins.get(key)
    if plugin is None and key != "unknown":
        return {
            "layer": "format-readers",
            "format": format_name,
            "plugin": None,
            "action": "stop-and-ask",
            "reason": "license MediaGenie Proteus or wrap — no half parser",
        }
    return {
        "layer": "format-readers",
        "format": format_name,
        "plugin": plugin or "generic",
        "available_plugins": sorted(plugins.keys()),
    }


def apply_media_rescue(*, degraded: bool = False, rescue_type: str | None = None) -> dict[str, Any]:
    if degraded:
        return {
            "layer": "media-rescue",
            "degraded": True,
            "rescue_type": rescue_type or "unknown",
            "action": "degraded-media-path",
            "stop_and_ask_crypto_bypass": rescue_type == "encrypted-without-keys",
        }
    return {"layer": "media-rescue", "degraded": False, "action": "normal-path"}


def apply_all_layers(
    *,
    job_id: str,
    module: str,
    files: Sequence[Path],
    root: Path | None,
    manifests_dir: Path,
    params: Mapping[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if files:
        results.append(
            apply_integrity(
                job_id=job_id,
                module=module,
                files=files,
                root=root,
                manifests_dir=manifests_dir,
                metadata={"source": params.get("source_path")},
            )
        )
    results.append(
        apply_ediscovery(
            custodians=params.get("custodians"),
            keywords=params.get("keywords"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            legal_holds=params.get("legal_holds"),
        )
    )
    if params.get("encrypt"):
        results.append(apply_kms_kmip(key_id=params.get("key_id"), encrypt=True))
    else:
        results.append(apply_kms_kmip(key_id=params.get("key_id"), encrypt=False))
    results.append(
        apply_worm(
            retention_days=params.get("retention_days"),
            mode=params.get("worm_mode", "governance"),
            erasure_requested=bool(params.get("erasure_requested")),
        )
    )
    results.append(apply_format_readers(format_name=params.get("backup_format")))
    results.append(
        apply_media_rescue(
            degraded=bool(params.get("degraded_media")),
            rescue_type=params.get("rescue_type"),
        )
    )
    return results
