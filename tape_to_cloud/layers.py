"""Six cross-cutting layers every tape-to-cloud module must call.

Integrity hashes are SHA-256 (MD5 is never primary). KMIP refuses a missing key.
Format readers are license-or-wrap. Media rescue never invents a crypto bypass.
WORM vs erasure is stop-and-ask. eDiscovery records holds and a defensibility log.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from tape_to_cloud.catalog import LAYERS, SAMPLE_JOB_ID

WRAP_PLUGIN = "wrap-mediagenie-proteus"
KMIP_SERVER = "kmip.demo.internal"
CIPHER = "AES-GCM-256"
WORM_DAYS = 2557
HOLD_ID = "HOLD-2024-0118"
CUSTODIAN = "j.lee"


class LayerError(Exception):
    """Hard stop from a cross-cutting layer (missing key, invented parser, crypto bypass)."""


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def apply_integrity(module_id: str, result: dict[str, Any]) -> dict[str, Any]:
    pre = sha256_hex(canonical_json({"module": module_id, "result": result}))
    sidecar_name = f"manifests/{SAMPLE_JOB_ID}/{module_id}.sha256.json"
    sidecar = {
        "algo": "SHA-256",
        "job_id": SAMPLE_JOB_ID,
        "module": module_id,
        "pre_sha256": pre,
        "sidecar": sidecar_name,
    }
    post = sha256_hex(canonical_json(sidecar))
    return {
        "primary_algo": "SHA-256",
        "md5_not_primary": True,
        "pre_hash": pre,
        "post_hash": post,
        "sidecar": sidecar_name,
        "signed": True,
    }


def apply_ediscovery(module_id: str) -> dict[str, Any]:
    return {
        "holds": [HOLD_ID],
        "custodians": [CUSTODIAN],
        "defensibility_log": f"logs/{SAMPLE_JOB_ID}/{module_id}-ediscovery.jsonl",
    }


def apply_kms_kmip(*, key_present: bool = True) -> dict[str, Any]:
    if not key_present:
        raise LayerError("KMIP key missing; refuse read (key is never on the cartridge)")
    return {
        "kmip_server": KMIP_SERVER,
        "cipher": CIPHER,
        "key_present": True,
        "refuse_if_missing": True,
    }


def apply_worm() -> dict[str, Any]:
    return {
        "policy": "S3 Object Lock COMPLIANCE + Tape Retention Lock COMPLIANCE",
        "retention_days": WORM_DAYS,
        "erasure_conflict": "stop-and-ask",
    }


def apply_format_readers(*, plugin: str = WRAP_PLUGIN, detected: str = "IBM Spectrum Protect / TSM") -> dict[str, Any]:
    if plugin != WRAP_PLUGIN:
        raise LayerError("format readers are license-or-wrap; do not invent a TSM/NetBackup parser")
    return {
        "plugin": plugin,
        "detected": detected,
        "invented_parser": False,
    }


def apply_media_rescue(*, crypto_bypass_attempted: bool = False, stiction: bool = False) -> dict[str, Any]:
    if crypto_bypass_attempted:
        raise LayerError("stop-and-ask: do not invent a crypto bypass for encrypted media")
    return {
        "condition": "stiction-watch" if stiction else "pass",
        "stiction": stiction,
        "crypto_bypass_attempted": False,
    }


def apply_layers(
    module_id: str,
    result: dict[str, Any],
    *,
    key_present: bool = True,
    crypto_bypass_attempted: bool = False,
) -> dict[str, Any]:
    """Run all six layers. Order: rescue → KMIP → format → integrity → WORM → eDiscovery."""
    rescue = apply_media_rescue(crypto_bypass_attempted=crypto_bypass_attempted)
    kmip = apply_kms_kmip(key_present=key_present)
    readers = apply_format_readers()
    integrity = apply_integrity(module_id, result)
    worm = apply_worm()
    ediscovery = apply_ediscovery(module_id)
    block = {
        "integrity": integrity,
        "ediscovery": ediscovery,
        "kms-kmip": kmip,
        "worm": worm,
        "format-readers": readers,
        "media-rescue": rescue,
    }
    if set(block) != set(LAYERS):
        raise LayerError(f"layer set mismatch: {sorted(block)} vs {list(LAYERS)}")
    return block
