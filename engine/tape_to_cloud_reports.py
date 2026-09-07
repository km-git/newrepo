"""Sample vendor-shaped Tape-to-Cloud reports with recomputed SHA-256 sidecars.

These are labeled SAMPLE / DEMO packages for the local hub. Hashes are SHA-256 of
canonical JSON (sorted keys, no pickle). MD5 and SHA-1 are refused.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from engine.tape_to_cloud_hub import (
    CROSS_CUTTING,
    CURSOR_RULES,
    DISCOVERY_DOCS,
    MODULES,
    ROOT,
    _discovery_dir,
)

SAMPLE_GENERATED_UTC = "2026-09-07T00:00:00+00:00"
HASH_ALG = "SHA-256"
REFUSED_HASH_ALGS = ("MD5", "SHA-1", "SHA1")


def _demo_sha256(label: str) -> str:
    """Deterministic SHA-256 for SAMPLE object payloads (not live customer bytes)."""
    return hashlib.sha256(f"tape-to-cloud-sample:{label}".encode()).hexdigest()


# Frozen so canonical SHA-256 is stable across process restarts.
_REPORT_BODIES: tuple[dict[str, Any], ...] | None = None


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    """SHA-256 of canonical JSON, excluding the digest field itself."""
    body = {k: v for k, v in payload.items() if k != "canonical_sha256"}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def attach_canonical_hash(report: dict[str, Any]) -> dict[str, Any]:
    out = dict(report)
    out["hash_algorithm"] = HASH_ALG
    out.pop("canonical_sha256", None)
    out["canonical_sha256"] = canonical_sha256(out)
    return out


def verify_report_hash(report: Mapping[str, Any]) -> bool:
    expected = report.get("canonical_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    return expected == canonical_sha256(report)


def _media_audit() -> dict[str, Any]:
    return {
        "id": "rpt-audit-cma-2026-q1",
        "kind": "media_audit",
        "title": "Comprehensive Media Audit — ACME vault pickup Q1 2026",
        "sample": True,
        "generated_utc": SAMPLE_GENERATED_UTC,
        "matter_id": "ACME-LEGAL-HOLD-2026-014",
        "status": "complete",
        "vendor_shape": "Tape Ark Comprehensive Media Audit (QR, 360-photo, RFID, degradation 1-10)",
        "modules": ["audit", "tape-ops", "tape-vault", "destroy"],
        "layers": ["integrity", "media-rescue"],
        "summary": (
            "48 cartridges photographed and RFID-scanned at vault intake. Two LTO-7 "
            "volumes flagged stiction (degradation 8); one 3592 Jaguar encrypted-without-keys "
            "stopped for counsel. Pre/post SHA-256 recorded; MD5/SHA-1 refused."
        ),
        "body": {
            "site": "Offsite vault aisle B-12 (courier CoC inbound)",
            "operator": "media-audit-bot@local",
            "totals": {
                "cartridges": 48,
                "photographed_360": 48,
                "rfid_mam_read": 47,
                "rfid_unreadable": 1,
                "duplicate_media": 2,
                "cloud_cost_forecast_usd": 18420.50,
            },
            "degradation_histogram": {
                "1-3": 31,
                "4-6": 14,
                "7-8": 2,
                "9-10": 1,
            },
            "cartridges": [
                {
                    "volser": "LTO8-4412-A",
                    "form_factor": "LTO-8",
                    "rfid_epc": "E2801170000000204412AA01",
                    "mam_barcode": "LTO84412A",
                    "qr": "tc://audit/LTO8-4412-A",
                    "photo_360": "s3://seaweedfs-audit/photos/LTO8-4412-A.jpg",
                    "degradation": 3,
                    "pre_sha256": _demo_sha256("LTO8-4412-A:pre"),
                    "post_sha256": _demo_sha256("LTO8-4412-A:pre"),
                    "match": True,
                    "flags": [],
                },
                {
                    "volser": "LTO7-1188-B",
                    "form_factor": "LTO-7",
                    "rfid_epc": "E2801170000000201188BB02",
                    "mam_barcode": "LTO71188B",
                    "qr": "tc://audit/LTO7-1188-B",
                    "photo_360": "s3://seaweedfs-audit/photos/LTO7-1188-B.jpg",
                    "degradation": 8,
                    "pre_sha256": _demo_sha256("LTO7-1188-B:pre"),
                    "post_sha256": None,
                    "match": False,
                    "flags": ["stiction", "oxide_loss", "degraded-media-path"],
                },
                {
                    "volser": "3592-77-C",
                    "form_factor": "IBM 3592 Jaguar TS1150",
                    "rfid_epc": None,
                    "mam_barcode": "JAG359277C",
                    "qr": "tc://audit/3592-77-C",
                    "photo_360": "s3://seaweedfs-audit/photos/3592-77-C.jpg",
                    "degradation": 2,
                    "pre_sha256": None,
                    "post_sha256": None,
                    "match": False,
                    "flags": ["encrypted-without-keys", "stop-and-ask", "no-crypto-bypass"],
                },
            ],
            "refused_hash_algorithms": list(REFUSED_HASH_ALGS),
            "notes": (
                "Degraded-media path is Temporal-durable; do not invent a TSM parser or "
                "crypto bypass on a cheap model. HDD rescue is in-scope for the same pickup."
            ),
        },
    }


def _ediscovery_production() -> dict[str, Any]:
    return {
        "id": "rpt-ediscovery-prod-hold-4412",
        "kind": "ediscovery_production",
        "title": "eDiscovery production package — hold 4412 (PST/NSF + defensibility log)",
        "sample": True,
        "generated_utc": SAMPLE_GENERATED_UTC,
        "matter_id": "ACME-LEGAL-HOLD-2026-014",
        "status": "hold",
        "vendor_shape": "Tape Ark email restore / Iron Mountain litigation restore (custodian/date/keyword)",
        "modules": ["email-extract", "email-migrate", "restore", "analytics"],
        "layers": ["ediscovery", "integrity", "format-readers"],
        "summary": (
            "Custodian + date + keyword production for three mailboxes. Legal hold is active. "
            "One GDPR Art. 17 erasure request is STOP_AND_ASK because WORM retention wins until counsel override."
        ),
        "body": {
            "filters": {
                "custodians": ["j.doe@acme.example", "a.nguyen@acme.example", "c.okonkwo@acme.example"],
                "date_from": "2018-01-01",
                "date_to": "2021-12-31",
                "keywords": ["Nexus", "purchase agreement", "board minutes"],
                "platforms": ["Exchange EDB", "PST", "Lotus NSF", "GroupWise"],
            },
            "legal_hold": {
                "hold_id": "HOLD-4412",
                "active": True,
                "issued_utc": "2026-03-12T14:00:00+00:00",
                "issuing_counsel": "outside-counsel@example.test",
            },
            "gdpr_conflict": {
                "regulation": "GDPR Art. 17",
                "subject": "j.doe@acme.example",
                "action": "STOP_AND_ASK",
                "reason": (
                    "WORM / SEC 17a-4 retention lock until 2033-12-31. Erasure cannot proceed "
                    "without written counsel override. Do not silently delete."
                ),
            },
            "packages": [
                {
                    "format": "PST",
                    "path": "s3://seaweedfs-ediscovery/hold-4412/j.doe.pst",
                    "messages": 18420,
                    "sha256": _demo_sha256("hold-4412:j.doe.pst"),
                    "malware_quarantined": 3,
                },
                {
                    "format": "NSF",
                    "path": "s3://seaweedfs-ediscovery/hold-4412/a.nguyen.nsf",
                    "messages": 6211,
                    "sha256": _demo_sha256("hold-4412:a.nguyen.nsf"),
                    "malware_quarantined": 0,
                },
                {
                    "format": "load_file",
                    "path": "s3://seaweedfs-ediscovery/hold-4412/DAT.dat",
                    "messages": 24631,
                    "sha256": _demo_sha256("hold-4412:DAT.dat"),
                    "malware_quarantined": 3,
                },
            ],
            "defensibility_log": [
                {
                    "utc": "2026-03-12T14:05:11+00:00",
                    "actor": "hold-service",
                    "event": "legal_hold_applied",
                    "detail": "HOLD-4412 on three custodians",
                },
                {
                    "utc": "2026-04-02T09:12:44+00:00",
                    "actor": "email-extract",
                    "event": "keyword_search_complete",
                    "detail": "3 keywords, 24,631 hits staged",
                },
                {
                    "utc": "2026-04-03T16:40:02+00:00",
                    "actor": "counsel-review",
                    "event": "privilege_screen",
                    "detail": "412 privilege hits withheld",
                },
            ],
            "delivery": ["cloud staging (SeaweedFS)", "encrypted USB", "encrypted DVD"],
        },
    }


def _worm_kmip_policy() -> dict[str, Any]:
    return {
        "id": "rpt-worm-kmip-policy-17a4",
        "kind": "worm_kmip_policy",
        "title": "WORM retention lock + KMIP envelope — SEC 17a-4 vs GDPR stop-and-ask",
        "sample": True,
        "generated_utc": SAMPLE_GENERATED_UTC,
        "matter_id": "ACME-LEGAL-HOLD-2026-014",
        "status": "in_progress",
        "vendor_shape": "AWS Tape Gateway Tape Retention Lock / GRAU FileLock GoBD / KMIP cluster",
        "modules": ["tape-saas", "tape-vault", "vtl-cloud"],
        "layers": ["worm", "kms-kmip", "integrity"],
        "summary": (
            "Object-lock class COMPLIANCE until 2033-12-31. LTO AES-256 data keys live in KMIP; "
            "cartridge never holds the key. GDPR erasure is queued as STOP_AND_ASK."
        ),
        "body": {
            "retention": {
                "policy_id": "SEC-17A4-7Y",
                "mode": "COMPLIANCE",
                "lock_until": "2033-12-31T23:59:59+00:00",
                "targets": ["S3 Object Lock", "GCS Bucket Lock", "Azure Immutable Blob", "SeaweedFS Filer"],
                "on_prem_default": "SeaweedFS",
            },
            "kmip": {
                "cluster": "kmip.vault.internal:5696",
                "key_uuid": "8f3c1e2a-9b44-4d11-a6e0-00c0ffee4412",
                "algorithm": "AES-256-GCM",
                "lto10_note": "LTO-10 quantum-safe AES-GCM-256; no LTO-10 backward read/write",
                "refuse_read_if_key_missing": True,
            },
            "conflicts": [
                {
                    "kind": "WORM_vs_erasure",
                    "action": "STOP_AND_ASK",
                    "detail": "GDPR Art. 17 subject request vs COMPLIANCE lock",
                }
            ],
            "minio_ce": {
                "archived": "2026-04-25",
                "recommendation": "SeaweedFS; do not deploy MinIO Community Edition",
            },
        },
    }


def _restore_coc() -> dict[str, Any]:
    return {
        "id": "rpt-restore-coc-job-8841",
        "kind": "restore_coc",
        "title": "Restore job 8841 — chain-of-custody event log",
        "sample": True,
        "generated_utc": SAMPLE_GENERATED_UTC,
        "matter_id": "ACME-LEGAL-HOLD-2026-014",
        "status": "complete",
        "vendor_shape": "Iron Mountain on-demand restore + courier CoC; Tape Ark mid-project restore",
        "modules": ["restore", "tape-vault", "tape-ops"],
        "layers": ["integrity", "ediscovery"],
        "summary": (
            "Job 8841 restored 2.4 TiB from LTO-8 to SeaweedFS staging. Eight CoC events from vault "
            "pickup through counsel download. Bit-for-bit SHA-256 verified at ingest and at handoff."
        ),
        "body": {
            "job_id": "RESTORE-8841",
            "bytes_restored": 2638827906662,
            "timeframe": "2019-Q3 NetBackup catalog (Cohesity-owned format — license-or-wrap)",
            "events": [
                {
                    "seq": 1,
                    "utc": "2026-05-01T08:02:00+00:00",
                    "actor": "vault-clerk",
                    "location": "vault B-12",
                    "event": "pickup",
                    "sha256": None,
                },
                {
                    "seq": 2,
                    "utc": "2026-05-01T11:18:00+00:00",
                    "actor": "courier",
                    "location": "sealed tote IRM-9921",
                    "event": "in_transit",
                    "sha256": None,
                },
                {
                    "seq": 3,
                    "utc": "2026-05-01T14:40:00+00:00",
                    "actor": "ingest-operator",
                    "location": "lab slot 4",
                    "event": "received_unsealed",
                    "sha256": None,
                },
                {
                    "seq": 4,
                    "utc": "2026-05-01T16:11:33+00:00",
                    "actor": "integrity-layer",
                    "location": "lab slot 4",
                    "event": "pre_image_sha256",
                    "sha256": _demo_sha256("restore-8841:pre-image"),
                },
                {
                    "seq": 5,
                    "utc": "2026-05-02T03:22:10+00:00",
                    "actor": "restore-worker",
                    "location": "Temporal workflow restore-8841",
                    "event": "restore_complete",
                    "sha256": _demo_sha256("restore-8841:objects"),
                },
                {
                    "seq": 6,
                    "utc": "2026-05-02T03:22:41+00:00",
                    "actor": "integrity-layer",
                    "location": "s3://seaweedfs-restore/8841/",
                    "event": "post_copy_sha256_match",
                    "sha256": _demo_sha256("restore-8841:objects"),
                },
                {
                    "seq": 7,
                    "utc": "2026-05-02T15:00:00+00:00",
                    "actor": "outside-counsel@example.test",
                    "location": "matter portal",
                    "event": "counsel_download",
                    "sha256": _demo_sha256("restore-8841:objects"),
                },
                {
                    "seq": 8,
                    "utc": "2026-05-02T15:01:12+00:00",
                    "actor": "integrity-layer",
                    "location": "matter portal",
                    "event": "handoff_hash_verified",
                    "sha256": _demo_sha256("restore-8841:objects"),
                },
            ],
        },
    }


def _integrity_sidecar() -> dict[str, Any]:
    return {
        "id": "rpt-integrity-sidecar-lto8-batch",
        "kind": "integrity_sidecar",
        "title": "Integrity sidecar manifest — LTO-8 batch (signed JSON, SHA-256 only)",
        "sample": True,
        "generated_utc": SAMPLE_GENERATED_UTC,
        "matter_id": "ACME-LEGAL-HOLD-2026-014",
        "status": "complete",
        "vendor_shape": "Iron Mountain Media Imaging sidecar + bit-for-bit verification",
        "modules": ["audit", "disk-ingest", "tape-duplicate"],
        "layers": ["integrity", "format-readers"],
        "summary": (
            "Per-object SHA-256 sidecar for 12,408 files. Format reader is license-or-wrap NetBackup; "
            "TSM is a separate plugin. Full tape image optional and not taken on this batch."
        ),
        "body": {
            "manifest_uri": "s3://seaweedfs-integrity/lto8-batch/manifest.json",
            "object_count": 12408,
            "bytes": 982734002112,
            "hash_algorithm": HASH_ALG,
            "refused": list(REFUSED_HASH_ALGS),
            "format_reader": {
                "plugin": "netbackup-wrap",
                "license_or_wrap": True,
                "owner_note": "Cohesity owns NetBackup; Backup Exec is Arctera",
                "tsm_plugin": "ibm-spectrum-protect-wrap",
            },
            "sample_objects": [
                {
                    "key": "nb/2019/q3/catalog.bin",
                    "bytes": 448821120,
                    "sha256": _demo_sha256("nb/2019/q3/catalog.bin"),
                },
                {
                    "key": "nb/2019/q3/media/LTO8-4412-A.img",
                    "bytes": 12094627905536,
                    "sha256": _demo_sha256("nb/2019/q3/media/LTO8-4412-A.img"),
                    "note": "optional full tape image — not stored this run",
                    "stored": False,
                },
            ],
            "signature": {
                "scheme": "detached-JWS-sample",
                "kid": "audit-signing-key-2026",
                "note": "SAMPLE: signature bytes omitted; production uses KMS-signed JWS",
            },
        },
    }


def _migration_volume_grid() -> dict[str, Any]:
    volumes = [
        {
            "volser": "TAPE01",
            "action": "COPY",
            "status": "SUCCESS",
            "bytes": 2_498_560_000_000,
            "plugin": "netbackup-wrap",
        },
        {
            "volser": "TAPE02",
            "action": "COPY",
            "status": "SUCCESS",
            "bytes": 1_933_012_000_000,
            "plugin": "netbackup-wrap",
        },
        {
            "volser": "TAPE03",
            "action": "COPY",
            "status": "FAIL",
            "bytes": 0,
            "plugin": "tsm-wrap",
            "error": "KMIP key missing",
        },
        {
            "volser": "TAPE04",
            "action": "COPY",
            "status": "IN_PROGRESS",
            "bytes": 812_000_000_000,
            "plugin": "veeam-wrap",
        },
        {
            "volser": "TAPE05",
            "action": "COPY",
            "status": "SUCCESS",
            "bytes": 3_102_441_000_000,
            "plugin": "commvault-wrap",
        },
        {
            "volser": "TAPE06",
            "action": "COPY",
            "status": "SUCCESS",
            "bytes": 2_010_000_000_000,
            "plugin": "networker-wrap",
        },
        {
            "volser": "TAPE07",
            "action": "COPY",
            "status": "IN_PROGRESS",
            "bytes": 104_000_000_000,
            "plugin": "data-protector-wrap",
        },
        {
            "volser": "TAPE08",
            "action": "COPY",
            "status": "FAIL",
            "bytes": 0,
            "plugin": "arcserve-wrap",
            "error": "stiction — media-rescue",
        },
    ]
    success = sum(1 for v in volumes if v["status"] == "SUCCESS")
    fail = sum(1 for v in volumes if v["status"] == "FAIL")
    in_progress = sum(1 for v in volumes if v["status"] == "IN_PROGRESS")
    return {
        "id": "rpt-migration-volume-grid-zvt",
        "kind": "migration_volume_grid",
        "title": "Migration volume grid — COPY / SUCCESS / FAIL / IN_PROGRESS",
        "sample": True,
        "generated_utc": SAMPLE_GENERATED_UTC,
        "matter_id": "ACME-MIGRATE-2026-088",
        "status": "in_progress",
        "vendor_shape": "Precisely zVT Migration Audit volume grid (COPY + summary totals)",
        "modules": ["vtl-cloud", "tape-duplicate", "disk-ingest", "analytics"],
        "layers": ["integrity", "format-readers", "kms-kmip", "media-rescue"],
        "summary": (
            f"{success} volumes SUCCESS, {fail} FAIL, {in_progress} IN_PROGRESS. "
            "On-prem VTL target is SeaweedFS. Failures are KMIP-miss and stiction — not silent skip."
        ),
        "body": {
            "grid": volumes,
            "totals": {
                "volumes": len(volumes),
                "success": success,
                "fail": fail,
                "in_progress": in_progress,
                "bytes_copied": sum(v["bytes"] for v in volumes if v["status"] == "SUCCESS"),
            },
            "target": {
                "on_prem": "SeaweedFS",
                "cloud_pool": "S3 Glacier Flexible Retrieval (hours) vs Deep Archive (5-12 h)",
                "iscsi_present_to": ["Cohesity DataProtect", "Rubrik", "NetBackup"],
            },
        },
    }


def _raw_reports() -> tuple[dict[str, Any], ...]:
    return (
        _media_audit(),
        _ediscovery_production(),
        _worm_kmip_policy(),
        _restore_coc(),
        _integrity_sidecar(),
        _migration_volume_grid(),
    )


def sample_reports() -> tuple[dict[str, Any], ...]:
    global _REPORT_BODIES
    if _REPORT_BODIES is None:
        _REPORT_BODIES = tuple(attach_canonical_hash(r) for r in _raw_reports())
    return _REPORT_BODIES


def get_report(report_id: str) -> dict[str, Any] | None:
    for report in sample_reports():
        if report["id"] == report_id:
            return report
    return None


def list_report_summaries(kind: str | None = None) -> list[dict[str, Any]]:
    rows = []
    for report in sample_reports():
        if kind and report["kind"] != kind:
            continue
        rows.append(
            {
                "id": report["id"],
                "kind": report["kind"],
                "title": report["title"],
                "status": report["status"],
                "matter_id": report["matter_id"],
                "modules": report["modules"],
                "layers": report["layers"],
                "canonical_sha256": report["canonical_sha256"],
                "hash_verified": verify_report_hash(report),
                "href": f"/tape-to-cloud/reports/{report['id']}",
                "api": f"/api/tape-to-cloud/reports/{report['id']}",
            }
        )
    return rows


def validate_intactness() -> dict[str, Any]:
    """Live check: 16 modules, 6 layers, discovery docs, cursor rules, report hashes."""
    discovery = _discovery_dir()
    docs = [
        {
            "file": name,
            "exists": (discovery / name).is_file(),
        }
        for name, _label in DISCOVERY_DOCS
    ]
    rules = [
        {
            "file": name,
            "exists": (ROOT / ".cursor" / "rules" / name).is_file(),
        }
        for name in CURSOR_RULES
    ]
    reports = [
        {
            "id": r["id"],
            "hash_algorithm": r.get("hash_algorithm"),
            "hash_verified": verify_report_hash(r),
            "refuses_md5_sha1": HASH_ALG == "SHA-256",
        }
        for r in sample_reports()
    ]
    expected_modules = (
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
    expected_layers = (
        "integrity",
        "ediscovery",
        "kms-kmip",
        "worm",
        "format-readers",
        "media-rescue",
    )
    checks = {
        "sixteen_modules": tuple(MODULES) == expected_modules,
        "six_layers": tuple(CROSS_CUTTING) == expected_layers,
        "discovery_docs_on_disk": all(d["exists"] for d in docs),
        "cursor_rules_on_disk": all(r["exists"] for r in rules),
        "sample_reports": len(reports) == 6,
        "all_report_hashes_verified": all(r["hash_verified"] for r in reports),
        "hash_algorithm_sha256": all(r["hash_algorithm"] == HASH_ALG for r in reports),
        "no_seventeenth_module": "brochure-17" not in MODULES,
    }
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "ok": all(checks.values()),
        "checks": checks,
        "modules": list(MODULES),
        "layers": list(CROSS_CUTTING),
        "discovery_docs": docs,
        "cursor_rules": rules,
        "reports": reports,
    }


def _css() -> str:
    return """
    :root { --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --green:#3fb950; --red:#f85149; --yellow:#d29922; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
    header { display:flex; justify-content:space-between; align-items:center; padding:1rem 1.25rem; border-bottom:1px solid var(--border); }
    h1 { margin:0; font-size:1.25rem; }
    .nav a { color:var(--accent); margin-left:1rem; text-decoration:none; }
    main { padding:1.25rem; max-width:1100px; margin:0 auto; }
    section { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:1rem 1.1rem; margin-bottom:1rem; }
    h2 { margin:0 0 0.75rem; font-size:1rem; }
    table { width:100%; border-collapse:collapse; font-size:0.9rem; }
    th, td { text-align:left; padding:0.45rem 0.5rem; border-bottom:1px solid var(--border); vertical-align:top; }
    .muted { color:var(--muted); font-size:0.85rem; }
    pre { background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:0.75rem; overflow:auto; font-size:0.75rem; }
    .ok { color:var(--green); }
    .bad { color:var(--red); }
    .hold { color:var(--yellow); }
    .badge { display:inline-block; padding:0.1rem 0.45rem; border-radius:999px; border:1px solid var(--border); font-size:0.75rem; margin-right:0.3rem; }
    a { color:var(--accent); }
    """


def _nav(active: str) -> str:
    links = (
        ("/monitor", "Monitor"),
        ("/monetize", "Monetize"),
        ("/tape-to-cloud", "Hub"),
        ("/tape-to-cloud/reports", "Reports"),
        ("/tape-to-cloud/validation", "Validation"),
    )
    parts = []
    for href, label in links:
        mark = " aria-current='page'" if label.lower() == active else ""
        parts.append(f"<a href='{href}'{mark}>{html.escape(label)}</a>")
    return "".join(parts)


def _shell(title: str, active: str, inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_css()}</style>
</head>
<body>
  <header>
    <div><h1>{html.escape(title)}</h1><div class="muted">SAMPLE / DEMO packages · SHA-256 canonical JSON · 16 modules + 6 layers</div></div>
    <nav class="nav">{_nav(active)}</nav>
  </header>
  <main>
    {inner}
  </main>
</body>
</html>"""


def _status_class(status: str) -> str:
    if status == "complete":
        return "ok"
    if status in ("hold", "in_progress"):
        return "hold"
    return "bad"


def render_reports_index_html(kind: str | None = None) -> str:
    rows = list_report_summaries(kind)
    filters = [
        "all",
        "media_audit",
        "ediscovery_production",
        "worm_kmip_policy",
        "restore_coc",
        "integrity_sidecar",
        "migration_volume_grid",
    ]
    filter_html = " ".join(
        f"<a class='badge' href='/tape-to-cloud/reports{'' if k == 'all' else '?kind=' + html.escape(k)}'>{html.escape(k)}</a>"
        for k in filters
    )
    body_rows = "\n".join(
        (
            "<tr>"
            f"<td><a href='{html.escape(r['href'])}'><code>{html.escape(r['id'])}</code></a></td>"
            f"<td>{html.escape(r['kind'])}</td>"
            f"<td>{html.escape(r['title'])}</td>"
            f"<td class='{_status_class(r['status'])}'>{html.escape(r['status'])}</td>"
            f"<td>{html.escape(r['matter_id'])}</td>"
            f"<td class='{'ok' if r['hash_verified'] else 'bad'}'>{'verified' if r['hash_verified'] else 'MISMATCH'}</td>"
            "</tr>"
        )
        for r in rows
    )
    inner = f"""
    <section>
      <h2>Sample detailed reports</h2>
      <p class="muted">Vendor-shaped demo packages for audit, eDiscovery, WORM/KMIP, restore CoC, integrity sidecar, and migration volume grid. JSON: <code>/api/tape-to-cloud/reports</code></p>
      <p>{filter_html}</p>
      <table>
        <thead><tr><th>ID</th><th>Kind</th><th>Title</th><th>Status</th><th>Matter</th><th>SHA-256</th></tr></thead>
        <tbody>{body_rows}</tbody>
      </table>
    </section>
    """
    return _shell("Tape-to-Cloud sample reports", "reports", inner)


def _kv_table(mapping: Mapping[str, Any]) -> str:
    rows = []
    for key, value in mapping.items():
        if isinstance(value, (dict, list)):
            rendered = f"<pre>{html.escape(json.dumps(value, indent=2, default=str))}</pre>"
        else:
            rendered = html.escape(str(value))
        rows.append(f"<tr><th>{html.escape(str(key))}</th><td>{rendered}</td></tr>")
    return "<table>" + "".join(rows) + "</table>"


def render_report_detail_html(report: Mapping[str, Any]) -> str:
    verified = verify_report_hash(report)
    badge = "verified" if verified else "MISMATCH"
    klass = "ok" if verified else "bad"
    modules = " ".join(f"<span class='badge'>{html.escape(m)}</span>" for m in report["modules"])
    layers = " ".join(f"<span class='badge'>{html.escape(m)}</span>" for m in report["layers"])
    payload = json.dumps(report, indent=2, default=str)
    inner = f"""
    <section>
      <h2>{html.escape(str(report["title"]))}</h2>
      <p class="muted">{html.escape(str(report["vendor_shape"]))} · matter <code>{html.escape(str(report["matter_id"]))}</code></p>
      <p>Status: <span class="{_status_class(str(report["status"]))}">{html.escape(str(report["status"]))}</span>
         · Hash: <span class="{klass}">{html.escape(HASH_ALG)} {html.escape(badge)}</span>
         · <code>{html.escape(str(report["canonical_sha256"]))}</code></p>
      <p>{html.escape(str(report["summary"]))}</p>
      <p>Modules: {modules}</p>
      <p>Layers: {layers}</p>
      <p class="muted">API: <a href="/api/tape-to-cloud/reports/{html.escape(str(report["id"]))}"><code>/api/tape-to-cloud/reports/{html.escape(str(report["id"]))}</code></a>
         · <a href="/tape-to-cloud/reports">All reports</a></p>
    </section>
    <section>
      <h2>Report body</h2>
      {_kv_table(report["body"])}
    </section>
    <section>
      <h2>Canonical JSON (hashed)</h2>
      <pre>{html.escape(payload)}</pre>
    </section>
    """
    return _shell(str(report["title"]), "reports", inner)


def render_unknown_report_html(report_id: str) -> str:
    inner = f"""
    <section>
      <h2>Unknown report</h2>
      <p class="bad">No sample report named <code>{html.escape(report_id)}</code>.</p>
      <p><a href="/tape-to-cloud/reports">Back to reports</a></p>
    </section>
    """
    return _shell("Unknown report", "reports", inner)


def render_validation_html() -> str:
    state = validate_intactness()
    check_rows = "\n".join(
        f"<tr><td><code>{html.escape(k)}</code></td><td class='{'ok' if v else 'bad'}'>{'yes' if v else 'NO'}</td></tr>"
        for k, v in state["checks"].items()
    )
    module_html = " ".join(f"<span class='badge'>{html.escape(m)}</span>" for m in state["modules"])
    layer_html = " ".join(f"<span class='badge'>{html.escape(m)}</span>" for m in state["layers"])
    report_rows = "\n".join(
        f"<tr><td><code>{html.escape(r['id'])}</code></td>"
        f"<td class='{'ok' if r['hash_verified'] else 'bad'}'>{'verified' if r['hash_verified'] else 'MISMATCH'}</td>"
        f"<td>{html.escape(str(r['hash_algorithm']))}</td></tr>"
        for r in state["reports"]
    )
    overall = "INTACT" if state["ok"] else "FAILED"
    inner = f"""
    <section>
      <h2>Intactness</h2>
      <p>Overall: <strong class="{"ok" if state["ok"] else "bad"}">{overall}</strong>
         · JSON: <code>/api/tape-to-cloud/validation</code></p>
      <table><thead><tr><th>Check</th><th>Pass</th></tr></thead><tbody>{check_rows}</tbody></table>
    </section>
    <section>
      <h2>16 modules</h2>
      <p>{module_html}</p>
      <h2>6 cross-cutting layers</h2>
      <p>{layer_html}</p>
    </section>
    <section>
      <h2>Sample report hashes</h2>
      <table><thead><tr><th>Report</th><th>SHA-256</th><th>Alg</th></tr></thead><tbody>{report_rows}</tbody></table>
    </section>
    """
    return _shell("Tape-to-Cloud validation", "validation", inner)


def dispatch_report_routes(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]] | None = None,
) -> tuple[int, dict[str, str], bytes] | None:
    if (method or "GET").upper() != "GET":
        return None
    path = path.rstrip("/") or "/"
    kind = None
    if query and query.get("kind"):
        kind = query["kind"][0]

    if path == "/tape-to-cloud/reports":
        body = render_reports_index_html(kind).encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, body

    if path.startswith("/tape-to-cloud/reports/"):
        report_id = path.rsplit("/", 1)[-1]
        report = get_report(report_id)
        if report is None:
            body = render_unknown_report_html(report_id).encode("utf-8")
            return 404, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, body
        body = render_report_detail_html(report).encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, body

    if path == "/tape-to-cloud/validation":
        body = render_validation_html().encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, body

    if path == "/api/tape-to-cloud/reports":
        payload = {"reports": list_report_summaries(kind), "count": len(list_report_summaries(kind))}
        body = json.dumps(payload, indent=2).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body

    if path.startswith("/api/tape-to-cloud/reports/"):
        report_id = path.rsplit("/", 1)[-1]
        report = get_report(report_id)
        if report is None:
            body = json.dumps({"error": "unknown_report", "id": report_id}).encode("utf-8")
            return 404, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body
        body = json.dumps(report, indent=2).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body

    if path == "/api/tape-to-cloud/validation":
        body = json.dumps(validate_intactness(), indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body

    return None
