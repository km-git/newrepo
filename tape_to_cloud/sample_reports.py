"""Deterministic, vendor-checked demo reports for every tape-to-cloud module."""

from __future__ import annotations

import hashlib
from typing import Any

from tape_to_cloud.catalog import (
    LAYERS,
    MODULE_CATALOG,
    MODULES,
    SAMPLE_CUSTOMER,
    SAMPLE_GENERATED_UTC,
    SAMPLE_JOB_ID,
)

LAYERS_CALLED = {layer: "applied" for layer in LAYERS}

# Research basis (not an affiliation): Tape Ark CMA, Iron Mountain DRMS/ITAD, AWS Tape Gateway.
CITATIONS = (
    {
        "id": "tapeark-cma",
        "title": "Tape Ark Comprehensive Media Audit",
        "url": "https://www.tapeark.com/comprehensive-media-audit/",
        "fields": "QR, 360 photography, RFID volume ±5%, degradation triage, duplicate estimate, cloud-cost forecast",
    },
    {
        "id": "ironmountain-drms",
        "title": "Iron Mountain data restoration / vaulting / ITAD",
        "url": "https://www.ironmountain.com/services/data-restoration-and-migration",
        "fields": "Chain of custody, custodian restore, encrypted delivery, NIST 800-88 certificate of destruction",
    },
    {
        "id": "aws-tape-gateway",
        "title": "AWS Tape Gateway WORM + Tape Retention Lock",
        "url": "https://aws.amazon.com/blogs/storage/protecting-archives-with-worm-and-tape-retention-lock/",
        "fields": "iSCSI VTL, WORM at create, COMPLIANCE/GOVERNANCE lock, Glacier Flexible / Deep Archive pools",
    },
    {
        "id": "lto-10",
        "title": "LTO-10: no backward read/write",
        "url": "https://www.lto.org/lto-10/",
        "fields": "Mixed-fleet drives required when the collection spans LTO generations",
    },
)

AUDIT_TAPE_KEYS = (
    "barcode",
    "qr",
    "rfid_mam",
    "media_type",
    "generation",
    "backup_format",
    "bytes_estimate",
    "rfid_accuracy",
    "degradation",
    "risk_band",
    "header_sha256",
    "photos_360",
    "label_ocr",
    "encrypted",
    "duplicate_suspect",
    "cloud_cost_forecast_usd",
)


def demo_sha256(label: str) -> str:
    return hashlib.sha256(f"t2c-demo:{label}".encode()).hexdigest()


def _coc(*steps: tuple[str, str, str]) -> list[dict[str, str]]:
    return [{"utc": ts, "event": event, "actor": actor} for ts, event, actor in steps]


def _kpis(**pairs: Any) -> list[dict[str, Any]]:
    return [{"label": k.replace("_", " "), "value": v} for k, v in pairs.items()]


_RESULTS: dict[str, dict[str, Any]] = {
    "audit": {
        "executive_summary": (
            "CMA of 2,144 pieces across 16 media types at Houston and Perth. RFID-derived "
            "volume ±5% is 412.6 TiB native / 188.4 TiB after duplicate suppression. "
            "LTO-4 + LTO-6 are 61% of cartridge count but 94% of bytes — ingest those first. "
            "18 cartridges score degradation ≥8 (stiction/oxide). LTO-10 is present: no "
            "backward read/write, so the drive mix stays mandatory. Written report for "
            "management includes cloud-cost by tier and a re-tape avoidance estimate."
        ),
        "kpis": _kpis(
            media_count=2144,
            unique_media_types=16,
            estimated_tib=412.6,
            after_dedup_tib=188.4,
            critical_risk=18,
            glacier_flexible_year_usd=18420,
        ),
        "collection": {
            "sites": ["Houston, TX", "Perth, WA"],
            "received_utc": "2026-08-12T02:10:00+00:00",
            "rfid_volume_accuracy": "±5%",
            "photograph_method": "cradle + mirrors (360°)",
            "qr_namespace": "t2c://acme/",
        },
        "media_profile": [
            {"generation": "LTO-4", "count": 702, "pct_count": 32.7, "tib": 84.1, "pct_bytes": 20.4, "risk": "high"},
            {
                "generation": "LTO-6",
                "count": 610,
                "pct_count": 28.5,
                "tib": 304.0,
                "pct_bytes": 73.7,
                "risk": "moderate",
            },
            {"generation": "LTO-7", "count": 220, "pct_count": 10.3, "tib": 18.2, "pct_bytes": 4.4, "risk": "low"},
            {"generation": "LTO-10", "count": 8, "pct_count": 0.4, "tib": 2.1, "pct_bytes": 0.5, "risk": "mixed-fleet"},
            {
                "generation": "3592 Jaguar",
                "count": 44,
                "pct_count": 2.1,
                "tib": 2.8,
                "pct_bytes": 0.7,
                "risk": "moderate",
            },
            {"generation": "T10000C", "count": 12, "pct_count": 0.6, "tib": 0.9, "pct_bytes": 0.2, "risk": "low"},
            {
                "generation": "DLT-S4 / AIT / DDS / other",
                "count": 548,
                "pct_count": 25.6,
                "tib": 0.5,
                "pct_bytes": 0.1,
                "risk": "triage",
            },
        ],
        "tapes": [
            {
                "barcode": "LTO6-ACME-01002",
                "qr": "t2c://acme/LTO6-ACME-01002",
                "rfid_mam": "IBM-LTO6-MAM-44A1",
                "media_type": "LTO cartridge",
                "generation": "LTO-6",
                "backup_format": "IBM Spectrum Protect / TSM",
                "bytes_estimate": 2_400_000_000_000,
                "rfid_accuracy": "±5%",
                "degradation": 4,
                "risk_band": "moderate",
                "header_sha256": demo_sha256("hdr-LTO6-ACME-01002"),
                "photos_360": 12,
                "label_ocr": "TSM FULL WK40 HOUSTON",
                "encrypted": True,
                "duplicate_suspect": False,
                "cloud_cost_forecast_usd": 96.10,
            },
            {
                "barcode": "LTO4-ACME-00017",
                "qr": "t2c://acme/LTO4-ACME-00017",
                "rfid_mam": "HP-LTO4-MAM-09EE",
                "media_type": "LTO cartridge",
                "generation": "LTO-4",
                "backup_format": "Cohesity NetBackup (legacy Veritas)",
                "bytes_estimate": 640_000_000_000,
                "rfid_accuracy": "±5%",
                "degradation": 9,
                "risk_band": "critical",
                "header_sha256": demo_sha256("hdr-LTO4-ACME-00017"),
                "photos_360": 12,
                "label_ocr": "NBU-OIL-1989-WELLLOG",
                "encrypted": False,
                "duplicate_suspect": True,
                "cloud_cost_forecast_usd": 22.40,
            },
            {
                "barcode": "3592-JAG-00088",
                "qr": "t2c://acme/3592-JAG-00088",
                "rfid_mam": "IBM-3592-E08",
                "media_type": "IBM 3592 Jaguar",
                "generation": "3592-E08",
                "backup_format": "IBM Spectrum Protect / TSM",
                "bytes_estimate": 10_000_000_000_000,
                "rfid_accuracy": "±5%",
                "degradation": 6,
                "risk_band": "high",
                "header_sha256": demo_sha256("hdr-3592-JAG-00088"),
                "photos_360": 12,
                "label_ocr": "MAINFRAME FIN CLOSE",
                "encrypted": True,
                "duplicate_suspect": False,
                "cloud_cost_forecast_usd": 310.00,
            },
            {
                "barcode": "LTO10-ACME-00003",
                "qr": "t2c://acme/LTO10-ACME-00003",
                "rfid_mam": "IBM-LTO10-MAM-QS",
                "media_type": "LTO cartridge",
                "generation": "LTO-10",
                "backup_format": "LTFS",
                "bytes_estimate": 30_000_000_000_000,
                "rfid_accuracy": "±5%",
                "degradation": 1,
                "risk_band": "mixed-fleet",
                "header_sha256": demo_sha256("hdr-LTO10-ACME-00003"),
                "photos_360": 12,
                "label_ocr": "LTFS SEISMIC 2026",
                "encrypted": True,
                "duplicate_suspect": False,
                "cloud_cost_forecast_usd": 840.00,
            },
        ],
        "risk_triage": {"critical": 18, "high": 44, "moderate": 210, "low": 1872},
        "duplicates": {"estimated_pct": 11.2, "bytes": 88_123_000_000_000, "cross_site": True},
        "cloud_cost": {
            "s3_standard_year_usd": 96200,
            "glacier_flexible_year_usd": 18420,
            "deep_archive_year_usd": 6110,
            "re_tape_avoidance_usd": 1_240_000,
            "note": "Demo ACME figures. Pattern (few generations hold most bytes) matches published CMA case studies.",
        },
        "recommendations": [
            "Ingest LTO-4 degradation ≥8 this month (media-rescue path; do not wait for re-tape).",
            "Keep mixed LTO-10 + down-rev drives; LTO-10 has no backward read/write.",
            "Suppress 11.2% duplicate bytes before Glacier Flexible ingest.",
            "License-or-wrap MediaGenie Proteus for TSM vs NetBackup; do not invent parsers.",
        ],
        "chain_of_custody": _coc(
            ("2026-08-12T02:10:00+00:00", "Received at Perth mass-ingest dock; barcodes scanned", "vault-ops"),
            ("2026-08-12T06:40:00+00:00", "QR applied; 360 photos; RFID/MAM read", "cma-line-2"),
            ("2026-08-13T01:00:00+00:00", "Signed SHA-256 sidecar for CMA catalog", "integrity"),
        ),
    },
    "analytics": {
        "executive_summary": (
            "Archive Insight over the CMA catalog: 1.20M objects, mixed retention on 7 tapes, "
            "legal hold HOLD-2024-0118, two orphan TSM catalogs. PII (email/PAN) tagged for "
            "ediscovery vs GDPR erasure stop-and-ask."
        ),
        "kpis": _kpis(
            objects=1_204_331, duplicate_tib=80.2, pii_email=1204, mixed_retention_tapes=7, orphan_catalogs=2
        ),
        "age_histogram": [
            {"bucket": "pre-2000", "objects": 44012, "tib": 6.1},
            {"bucket": "2000-2010", "objects": 190441, "tib": 40.4},
            {"bucket": "2011-2020", "objects": 702110, "tib": 98.8},
            {"bucket": "2021+", "objects": 267768, "tib": 43.1},
        ],
        "legal_holds": [{"id": "HOLD-2024-0118", "custodian": "j.lee", "scope": "well-log + email"}],
        "pii_hits": {"email": 1204, "pan": 12, "ssn": 0},
        "recommendations": [
            "Do not file-level dispose objects on HOLD-2024-0118.",
            "Rebuild orphan TSM catalogs before VTL cutover.",
        ],
        "chain_of_custody": _coc(
            ("2026-08-14T00:00:00+00:00", "Insight index built from CMA + TSM catalog", "analytics")
        ),
    },
    "vtl-cloud": {
        "executive_summary": (
            "SeaweedFS on-prem VTL (1,500 slot) presented over iSCSI to TSM and Cohesity DataProtect. "
            "Custom tape pool ACME-COMPLIANCE: WORM at create, Tape Retention Lock COMPLIANCE 2,557 days "
            "(cannot be shortened, including root). Glacier Flexible 30d then Deep Archive 180d. "
            "Snowball Edge import completed for the Houston parcel."
        ),
        "kpis": _kpis(slots=1500, worm_tapes=220, retention_lock_days=2557, snowball_tib=48.0),
        "vtl": {
            "name": "seaweedfs-vtl-01",
            "emulation": "iSCSI medium-changer + tape drives",
            "iscsi_media_changer": "iqn.2026-09.com.acme:vtl-01-changer",
            "iscsi_drives": ["iqn.2026-09.com.acme:vtl-01-drive-0", "iqn.2026-09.com.acme:vtl-01-drive-1"],
            "barcode_prefix": "ACME",
            "presented_to": ["IBM Spectrum Protect", "Cohesity DataProtect"],
        },
        "tape_pool": {
            "id": "ACME-COMPLIANCE",
            "storage_class": "GLACIER",
            "worm_at_create": True,
            "retention_lock_type": "COMPLIANCE",
            "retention_lock_days": 2557,
            "max_lock_days": 36500,
            "bypass_governance_not_applicable": True,
        },
        "lifecycle": [
            {"day": 0, "class": "S3 Standard (staging)"},
            {"day": 30, "class": "Glacier Flexible Retrieval"},
            {"day": 180, "class": "Glacier Deep Archive"},
        ],
        "snowball": {"device": "Snowball Edge", "status": "imported", "job": "JOB-DEMO-ACME-LTO-SB1"},
        "recommendations": ["Keep COMPLIANCE lock; erasure requests stop-and-ask against HOLD-2024-0118."],
        "chain_of_custody": _coc(
            ("2026-08-20T00:00:00+00:00", "VTL pool created with COMPLIANCE retention lock", "vtl-cloud"),
            ("2026-08-21T12:00:00+00:00", "Snowball checksum vs CMA catalog", "integrity"),
        ),
    },
    "restore": {
        "executive_summary": (
            "Mid-project selective restore for custodian j.lee, keyword well-log, from 2014-01-01. "
            "318 objects, file-extract (not bit-image). Delivery: S3 prefix plus optional encrypted USB. "
            "Full chain of custody; catalogs rebuilt for degraded NBU tape LTO4-ACME-00017."
        ),
        "kpis": _kpis(objects_restored=318, bytes=42_001_992, custodians=1, virus_quarantine=0),
        "filters": {"custodian": "j.lee", "date_from": "2014-01-01", "keyword": "well-log", "hold": "HOLD-2024-0118"},
        "delivery": [
            {"channel": "s3", "uri": "s3://acme-restore/job-demo/j-lee/"},
            {"channel": "encrypted-usb", "uri": "optional", "standard": "Iron Mountain-style encrypted USB/DVD"},
        ],
        "mode": "file-extract",
        "bit_image": False,
        "rebuilt_catalogs": ["NBU-OIL-1989-WELLLOG"],
        "recommendations": ["Keep production package with defensibility log for counsel."],
        "chain_of_custody": _coc(
            ("2026-09-01T08:00:00+00:00", "Restore ticket RST-441 opened", "legal"),
            ("2026-09-01T11:22:00+00:00", "Objects hashed SHA-256 post-extract", "integrity"),
            ("2026-09-01T14:00:00+00:00", "Staged to S3 + USB option recorded", "restore"),
        ),
    },
    "disk-ingest": {
        "executive_summary": "USB HDD, NAS, and Snowball Edge ingest with HDD-rescue at 97.4% recovered. Manifest SHA-256 signed. No crypto bypass.",
        "kpis": _kpis(bytes_ingested=3_221_225_472_000, hdd_recovered_pct=97.4, snowball_jobs=1),
        "media": [
            {"id": "USB-HDD-4TB", "kind": "USB HDD", "bytes": 4_000_000_000_000, "rescue": False},
            {"id": "NAS-nfs://vault/proj", "kind": "NAS", "bytes": 8_000_000_000_000, "rescue": False},
            {"id": "Snowball-EDGE-01", "kind": "Snowball Edge", "bytes": 48_000_000_000_000, "rescue": False},
            {"id": "HDD-FAIL-19", "kind": "HDD rescue", "bytes": 1_221_225_472_000, "rescue": True},
        ],
        "hdd_rescue": {"attempted": True, "recovered_pct": 97.4, "crypto_bypass_attempted": False},
        "manifest_sha256": demo_sha256("disk-ingest-manifest"),
        "recommendations": ["Image remaining 2.6% unreadable sectors; do not invent a key."],
        "chain_of_custody": _coc(("2026-08-18T00:00:00+00:00", "Disk ingest manifest signed", "disk-ingest")),
    },
    "email-extract": {
        "executive_summary": "EDB + PST + NSF extract: 86 mailboxes, 1.10M messages, 14 ClamAV/YARA quarantine, 209 eDiscovery hits.",
        "kpis": _kpis(mailboxes=86, messages=1_104_220, quarantine=14, ediscovery_hits=209),
        "stores": [
            {"format": "EDB", "mailboxes": 40, "messages": 510_220},
            {"format": "PST", "mailboxes": 31, "messages": 402_000},
            {"format": "NSF", "mailboxes": 15, "messages": 192_000},
        ],
        "custodians": ["j.lee", "r.okonkwo", "legal-hold-box"],
        "recommendations": ["Load only cleaned stores into M365; keep quarantine offline."],
        "chain_of_custody": _coc(("2026-09-02T00:00:00+00:00", "Mailbox extract + virus scan", "email-extract")),
    },
    "email-migrate": {
        "executive_summary": "GroupWise + Exchange 2010 → Microsoft 365. 86 mailboxes, 190,441 dupes removed. NCP retirement scheduled. Workspace not in this wave.",
        "kpis": _kpis(mailboxes_migrated=86, dedup_removed=190_441, target="Microsoft 365"),
        "waves": [
            {"wave": 1, "source": "Exchange 2010", "mailboxes": 40, "status": "done"},
            {"wave": 2, "source": "GroupWise", "mailboxes": 46, "status": "done"},
        ],
        "ncp_retirement": "scheduled",
        "recommendations": ["Retire Novell NCP after 30-day dual-delivery."],
        "chain_of_custody": _coc(("2026-09-03T00:00:00+00:00", "M365 migration batch closed", "email-migrate")),
    },
    "tape-duplicate": {
        "executive_summary": "1-to-2 duplication of LTO7-ACME-00421 on seismic SEG-Y path. SHA-256 match on both targets. Signed manifest.",
        "kpis": _kpis(source="LTO7-ACME-00421", targets=2, verified=True),
        "copies": [
            {"barcode": "LTO7-COPY-A", "sha256": demo_sha256("dup-A"), "match": True},
            {"barcode": "LTO7-COPY-B", "sha256": demo_sha256("dup-B"), "match": True},
        ],
        "path": "seismic/SEG-Y",
        "signed_manifest": "manifests/LTO7-ACME-00421.dup.sha256.json",
        "recommendations": ["Vault COPY-B offsite; keep COPY-A in library."],
        "chain_of_custody": _coc(("2026-08-22T00:00:00+00:00", "1-to-N verify + signed sidecar", "tape-duplicate")),
    },
    "media-ingest": {
        "executive_summary": "Betacam SP + DICOM proxies via mediainfo/ffmpeg/Media2Cloud into s3://acme-media/proxies/.",
        "kpis": _kpis(items=2, proxy_hours=0.53, pipeline="Media2Cloud"),
        "items": [
            {
                "id": "BETACAM-SP-019",
                "kind": "Betacam SP",
                "proxy": "h264-720p",
                "duration_s": 1920,
                "sha256": demo_sha256("beta-019"),
            },
            {
                "id": "DICOM-STUDY-77",
                "kind": "DICOM",
                "proxy": "jpeg-series",
                "frames": 240,
                "sha256": demo_sha256("dicom-77"),
            },
        ],
        "target_prefix": "s3://acme-media/proxies/",
        "recommendations": ["Retain originals on WORM prefix; proxies are not the record copy."],
        "chain_of_custody": _coc(("2026-08-25T00:00:00+00:00", "Proxy + original hashes recorded", "media-ingest")),
    },
    "tape-ops": {
        "executive_summary": "IBM TS4500 health: 11/12 drives healthy, mtx robotics OK, onsite crew 2026-09-14, next CMA 2026-09-21 AEST.",
        "kpis": _kpis(library="IBM TS4500", drives_healthy=11, drives_degraded=1, next_audit="2026-09-21"),
        "drives": [
            {"id": "DRV01", "status": "healthy"},
            {"id": "DRV07", "status": "degraded", "note": "clean required"},
        ],
        "robotics": "mtx ok",
        "onsite_mobilization": "crew window 2026-09-14",
        "recommendations": ["Replace DRV07 cleaning brush before LTO-4 rescue window."],
        "chain_of_custody": _coc(("2026-09-07T00:00:00+00:00", "Library health snapshot", "tape-ops")),
    },
    "tape-saas": {
        "executive_summary": "Nexus tenant acme-energy: MFA, immutable catalog, file-level dispose blocked on 88 hold objects, dept billing exploration vs legal.",
        "kpis": _kpis(users=42, mfa=True, dispose_blocked=88, exploration_usd=8120.15),
        "tenant": "acme-energy",
        "file_level_dispose": {"eligible": 1204, "blocked_by_hold": 88},
        "dept_billing": [{"dept": "exploration", "usd": 8120.15}, {"dept": "legal", "usd": 440.00}],
        "immutable_catalog": True,
        "recommendations": ["Counsel signs hold release before file-level dispose."],
        "chain_of_custody": _coc(("2026-09-07T00:00:00+00:00", "Tenant billing period closed", "tape-saas")),
    },
    "tape-vault": {
        "executive_summary": (
            "310 residual cartridges in offsite-BNE-02. Courier CoC COC-2026-0907-441, barcode-level "
            "scan, 4h RTO, air-gap 3-2-1-0. 24/7 recall path."
        ),
        "kpis": _kpis(residual_cartridges=310, rto_hours=4, vault="offsite-BNE-02"),
        "courier": {"coc": "COC-2026-0907-441", "vehicle": "dedicated-media", "barcode_scans": 310},
        "air_gap": "3-2-1-0",
        "library_move": None,
        "recommendations": ["Keep residual LTO-4 criticals until cloud restore is proven."],
        "chain_of_custody": _coc(
            ("2026-09-06T22:00:00+00:00", "Pickup scanned", "courier"),
            ("2026-09-07T04:10:00+00:00", "Vault-in scanned", "vault-ops"),
        ),
    },
    "destroy": {
        "executive_summary": (
            "12 released cartridges degaussed then shredded (NIST SP 800-88 Rev. 1 Clear/Purge + "
            "DIN 66399 P-5). Certificate ITAD-CERT-2026-0907-12. Zero hold-blocked items."
        ),
        "kpis": _kpis(items=12, hold_blocked=0, certificate="ITAD-CERT-2026-0907-12"),
        "certificate": {
            "id": "ITAD-CERT-2026-0907-12",
            "issued_utc": SAMPLE_GENERATED_UTC,
            "nist": "NIST SP 800-88 Rev. 1",
            "irs": "IRS Pub 1075",
            "din_66399": "P-5",
            "method": "degauss + shred",
            "witness": "itad-officer-demo",
        },
        "items": [
            {"barcode": "LTO3-SCRAP-01", "method": "degauss+shred", "hold": False},
            {"barcode": "HDD-FAIL-19-platter", "method": "shred", "hold": False},
        ],
        "recommendations": ["File certificate with legal; do not destroy HOLD-2024-0118 media."],
        "chain_of_custody": _coc(
            ("2026-09-07T09:00:00+00:00", "Released from vault", "tape-vault"),
            ("2026-09-07T12:00:00+00:00", "Certificate issued", "destroy"),
        ),
    },
    "llm-corpus": {
        "executive_summary": "1,842 files → 1,510 after dedup, PII scrubbed (Presidio), 12.4M tokens, Dolma-like JSONL.",
        "kpis": _kpis(files_in=1842, after_dedup=1510, tokens=12_400_000, pii_scrubbed=True),
        "output_prefix": "s3://acme-llm/corpus/job-demo/",
        "format": "Dolma-like JSONL shards",
        "recommendations": ["Keep legal-hold docs out of the LLM corpus."],
        "chain_of_custody": _coc(("2026-09-04T00:00:00+00:00", "Corpus shards hashed", "llm-corpus")),
    },
    "ml-enrich": {
        "executive_summary": "OCR 4,401 pages, 18.5h transcribe, 7 DICOM studies, 22 SEG traces. Labels: well-log, contract, seismic-line.",
        "kpis": _kpis(ocr_pages=4401, transcribe_hours=18.5, dicom_studies=7, seg_traces=22),
        "labels": ["well-log", "contract", "seismic-line"],
        "recommendations": ["Human-review PAN hits before publishing labels."],
        "chain_of_custody": _coc(("2026-09-05T00:00:00+00:00", "Enrichment batch signed", "ml-enrich")),
    },
    "monetize": {
        "executive_summary": "1,510 assets tagged internal-research. Access policy JSON issued. Royalty $0 this period (no third-party reuse).",
        "kpis": _kpis(assets_tagged=1510, license_class="internal-research", royalty_usd=0.0),
        "access_policy": "s3://acme-policies/job-demo.json",
        "royalty_period": "2026-09",
        "recommendations": ["Do not enable third-party license class without legal review."],
        "chain_of_custody": _coc(("2026-09-07T00:00:00+00:00", "License tags + audit log append", "monetize")),
    },
}


def _layer_block(module_id: str) -> dict[str, Any]:
    pre = demo_sha256(f"pre:{module_id}")
    post = demo_sha256(f"post:{module_id}")
    return {
        "integrity": {
            "primary_algo": "SHA-256",
            "md5_not_primary": True,
            "pre_hash": pre,
            "post_hash": post,
            "sidecar": f"manifests/{SAMPLE_JOB_ID}/{module_id}.sha256.json",
            "signed": True,
        },
        "ediscovery": {
            "holds": ["HOLD-2024-0118"],
            "custodians": ["j.lee"],
            "defensibility_log": f"logs/{SAMPLE_JOB_ID}/{module_id}-ediscovery.jsonl",
        },
        "kms-kmip": {
            "kmip_server": "kmip.demo.internal",
            "cipher": "AES-GCM-256",
            "key_present": True,
            "refuse_if_missing": True,
        },
        "worm": {
            "policy": "S3 Object Lock COMPLIANCE + Tape Retention Lock COMPLIANCE",
            "retention_days": 2557,
            "erasure_conflict": "stop-and-ask",
        },
        "format-readers": {
            "plugin": "wrap-mediagenie-proteus",
            "detected": "IBM Spectrum Protect / TSM",
            "invented_parser": False,
        },
        "media-rescue": {
            "condition": "pass",
            "stiction": False,
            "crypto_bypass_attempted": False,
        },
    }


def report_id_for(module_id: str) -> str:
    return str(MODULE_CATALOG[module_id]["sample_report_id"])


def build_module_report(module_id: str) -> dict[str, Any]:
    if module_id not in MODULE_CATALOG:
        raise KeyError(module_id)
    spec = MODULE_CATALOG[module_id]
    result = _RESULTS[module_id]
    return {
        "report_id": spec["sample_report_id"],
        "kind": "sample",
        "disclaimer": "Synthetic demo data. Not a customer record. Citations are research basis, not a vendor affiliation.",
        "generated_utc": SAMPLE_GENERATED_UTC,
        "job_id": SAMPLE_JOB_ID,
        "customer": SAMPLE_CUSTOMER,
        "module": module_id,
        "menu": spec["menu"],
        "deliverable": spec["deliverable"],
        "citations": list(CITATIONS),
        "layers_called": dict(LAYERS_CALLED),
        "layers": _layer_block(module_id),
        "result": result,
        "kpis": result.get("kpis", []),
        "executive_summary": result.get("executive_summary", ""),
        "recommendations": result.get("recommendations", []),
        "chain_of_custody": result.get("chain_of_custody", []),
    }


def build_job_pack() -> dict[str, Any]:
    reports = [build_module_report(m) for m in MODULES]
    return {
        "report_id": "T2C-SAMPLE-JOB-PACK-20260907",
        "kind": "sample-job-pack",
        "disclaimer": "Synthetic demo data. Not a customer record.",
        "generated_utc": SAMPLE_GENERATED_UTC,
        "job_id": SAMPLE_JOB_ID,
        "customer": SAMPLE_CUSTOMER,
        "menu": "Combined job pack (all 16 modules)",
        "module_count": len(reports),
        "layer_count": len(LAYERS),
        "modules": [r["module"] for r in reports],
        "citations": list(CITATIONS),
        "executive_summary": (
            "ACME Energy demo job: CMA 2,144 media / 16 types, VTL COMPLIANCE lock, "
            "selective restore for HOLD-2024-0118, ITAD certificate for 12 released items."
        ),
        "kpis": _kpis(modules=16, layers=6, media_count=2144, unique_media_types=16, restore_objects=318),
        "index": [
            {
                "module": r["module"],
                "menu": r["menu"],
                "report_id": r["report_id"],
                "href": f"/tape-to-cloud/reports/{r['module']}",
                "headline": r["executive_summary"][:180],
            }
            for r in reports
        ],
        "reports": reports,
    }


def list_reports() -> list[dict[str, str]]:
    rows = [
        {
            "report_id": report_id_for(m),
            "module": m,
            "menu": MODULE_CATALOG[m]["menu"],
            "href": f"/tape-to-cloud/reports/{m}",
            "json": f"/api/tape-to-cloud/reports/{m}",
        }
        for m in MODULES
    ]
    rows.append(
        {
            "report_id": "T2C-SAMPLE-JOB-PACK-20260907",
            "module": "job-pack",
            "menu": "Combined job pack (all 16 modules)",
            "href": "/tape-to-cloud/reports/job-pack",
            "json": "/api/tape-to-cloud/reports/job-pack",
        }
    )
    return rows


def get_report(report_key: str) -> dict[str, Any]:
    key = report_key.strip().lower()
    if key in {"job-pack", "job_pack", "all"}:
        return build_job_pack()
    if key.startswith("t2c-sample-"):
        for module_id in MODULES:
            if report_id_for(module_id).lower() == key:
                return build_module_report(module_id)
        if key == "t2c-sample-job-pack-20260907":
            return build_job_pack()
    if key in MODULE_CATALOG:
        return build_module_report(key)
    raise KeyError(report_key)
