"""16-module map plus six cross-cutting layers for the tape-to-cloud hub."""

from __future__ import annotations

from typing import Any

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

LAYERS: tuple[str, ...] = (
    "integrity",
    "ediscovery",
    "kms-kmip",
    "worm",
    "format-readers",
    "media-rescue",
)

MODULE_CATALOG: dict[str, dict[str, Any]] = {
    "audit": {
        "menu": "Comprehensive Media Audit",
        "deliverable": (
            "Per-tape JSON: barcode/QR, RFID/MAM, 360 photos, format, byte estimate, "
            "degradation 1-10, header hash, file list, cloud-cost forecast."
        ),
        "sources": "LTO-1..LTO-10, 3592, T10000, DLT/AIT/DDS, VTL, optical, USB/NAS",
        "sample_report_id": "T2C-SAMPLE-AUDIT-20260907",
    },
    "analytics": {
        "menu": "Archive Insight",
        "deliverable": (
            "File/server-level SQL view: age, duplicates, PII, mixed retention, legal hold, orphan catalogs."
        ),
        "sources": "Catalog DB over audit + restore indexes",
        "sample_report_id": "T2C-SAMPLE-ANALYTICS-20260907",
    },
    "vtl-cloud": {
        "menu": "Tape Migration: Virtualization",
        "deliverable": (
            "Tape Gateway / StarWind / SeaweedFS VTL + iSCSI to original backup app + lifecycle + WORM/retention lock."
        ),
        "sources": "Physical library or Snowball offline path",
        "sample_report_id": "T2C-SAMPLE-VTL-CLOUD-20260907",
    },
    "restore": {
        "menu": "Tape Migration: Restore",
        "deliverable": (
            "On-demand read; eDiscovery filters; PST/NSF/EDB or encrypted USB; "
            "mid-project restore; file extract or bit-image."
        ),
        "sources": "VTL, physical drive, or staged object prefix",
        "sample_report_id": "T2C-SAMPLE-RESTORE-20260907",
    },
    "disk-ingest": {
        "menu": "Disk-Based Data Ingest",
        "deliverable": ("USB/NAS/SAN/RDX/optical/HDD + Snowball/Data Box; HDD-rescue path; manifest."),
        "sources": "Disk, RDX, UDO/ODA, flash, Snowball/Data Box",
        "sample_report_id": "T2C-SAMPLE-DISK-INGEST-20260907",
    },
    "email-extract": {
        "menu": "Email Restore From Tape",
        "deliverable": (
            "GroupWise, Lotus, Notes, Exchange, PST, EDB, NSF; user/date/keyword; virus quarantine; eDiscovery."
        ),
        "sources": "Backup-app tape with mailbox stores",
        "sample_report_id": "T2C-SAMPLE-EMAIL-EXTRACT-20260907",
    },
    "email-migrate": {
        "menu": "GroupWise to M365",
        "deliverable": (
            "GroupWise/Lotus/Exchange Post Office → M365 or Google Workspace or PST; dedup; Novell NCP retirement."
        ),
        "sources": "Extracted mail stores + virus-clean queue",
        "sample_report_id": "T2C-SAMPLE-EMAIL-MIGRATE-20260907",
    },
    "tape-duplicate": {
        "menu": "Tape Copy and Duplication",
        "deliverable": "1-to-N hardware duplication, seismic/SEG path, hash verification, signed manifests.",
        "sources": "Source cartridge + N blank targets",
        "sample_report_id": "T2C-SAMPLE-TAPE-DUPLICATE-20260907",
    },
    "media-ingest": {
        "menu": "Video Digitization",
        "deliverable": "LTO + Betacam/VHS/DigiBeta/DVC + DICOM → proxy/transcode → S3 + Media2Cloud.",
        "sources": "Broadcast videotape, CCTV, medical imaging, LTO media archives",
        "sample_report_id": "T2C-SAMPLE-MEDIA-INGEST-20260907",
    },
    "tape-ops": {
        "menu": "Legacy Tape Management",
        "deliverable": "Barcode/RFID, mtx robotics, drive/library health, scheduled audit, onsite mobilization.",
        "sources": "IBM/Oracle/Quantum/Spectra libraries",
        "sample_report_id": "T2C-SAMPLE-TAPE-OPS-20260907",
    },
    "tape-saas": {
        "menu": "Cloud-based Legacy Tape Mgmt (Nexus)",
        "deliverable": (
            "Tenant-isolated VTL, restore portal, file-level retain/delete, dept billing, MFA, immutable catalog."
        ),
        "sources": "Multi-tenant object catalog over migrated media",
        "sample_report_id": "T2C-SAMPLE-TAPE-SAAS-20260907",
    },
    "tape-vault": {
        "menu": "Tape Storage",
        "deliverable": (
            "Offsite-vault APIs, courier chain-of-custody, 24/7 DR, library moves, residual physical tape."
        ),
        "sources": "Residual cartridges after cloud copy",
        "sample_report_id": "T2C-SAMPLE-TAPE-VAULT-20260907",
    },
    "destroy": {
        "menu": "Media Destruction",
        "deliverable": (
            "Wipe / degauss / shred / incinerate; NIST 800-88 + IRS Pub 1075 certificate; ITAD of drives/libraries."
        ),
        "sources": "Cartridges, HDDs, libraries released from hold",
        "sample_report_id": "T2C-SAMPLE-DESTROY-20260907",
    },
    "llm-corpus": {
        "menu": "Legacy Data for LLM",
        "deliverable": "Extract → dedup → PII-scrub → tokenize → RAG / private-GPT format.",
        "sources": "Liberated file sets after restore",
        "sample_report_id": "T2C-SAMPLE-LLM-CORPUS-20260907",
    },
    "ml-enrich": {
        "menu": "AI and ML Services",
        "deliverable": "Rekognition / Transcribe / Comprehend / Textract + DICOM / seismic / OCR.",
        "sources": "Proxies, PDFs, DICOM, SEG traces",
        "sample_report_id": "T2C-SAMPLE-ML-ENRICH-20260907",
    },
    "monetize": {
        "menu": "Monetization Strategy",
        "deliverable": "License tagging, access control, royalty reporting, optional packaging adapter.",
        "sources": "Cataloged assets with license class",
        "sample_report_id": "T2C-SAMPLE-MONETIZE-20260907",
    },
}

LAYER_CATALOG: dict[str, dict[str, str]] = {
    "integrity": {
        "title": "Integrity / chain of custody",
        "deliverable": (
            "Pre/post SHA-256 (not MD5/SHA-1 as primary), signed sidecar manifest, optional full tape image."
        ),
    },
    "ediscovery": {
        "title": "eDiscovery",
        "deliverable": "Legal-hold graph, custodian/date/keyword production package, defensibility log.",
    },
    "kms-kmip": {
        "title": "KMS / KMIP",
        "deliverable": "LTO AES-256 / AES-GCM-256, KMIP client, envelope encrypt; refuse read if the key is missing.",
    },
    "worm": {
        "title": "WORM / immutability",
        "deliverable": "S3 Object Lock / GCS Bucket Lock / Azure Immutable Blob / Tape Retention Lock; GoBD/SEC 17a-4.",
    },
    "format-readers": {
        "title": "Format readers",
        "deliverable": (
            "Plugin table for TSM/NetBackup/Backup Exec/ARCserve/NetWorker/Data Protector/"
            "CommVault/Veeam/DPX/M&E; license-or-wrap."
        ),
    },
    "media-rescue": {
        "title": "Media rescue",
        "deliverable": (
            "Stiction / oxide-loss / reverse-wound / broken-tape / HDD-rescue path; stop-and-ask before crypto bypass."
        ),
    },
}

TARGETS = (
    "AWS S3 / Glacier Flexible / Deep Archive",
    "Azure Blob (Hot/Cool/Archive)",
    "Google Cloud Storage",
    "Backblaze B2",
    "Wasabi",
    "Cloudian",
    "SeaweedFS (on-prem S3 default)",
    "Ceph",
)

SAMPLE_JOB_ID = "JOB-DEMO-ACME-LTO"
SAMPLE_CUSTOMER = "ACME Energy (demo)"
SAMPLE_GENERATED_UTC = "2026-09-07T00:00:00+00:00"


def module_ids() -> tuple[str, ...]:
    return MODULES


def layer_ids() -> tuple[str, ...]:
    return LAYERS


def get_module(module_id: str) -> dict[str, Any]:
    spec = MODULE_CATALOG[module_id]
    return {"id": module_id, **spec}


def catalog_snapshot() -> dict[str, Any]:
    return {
        "module_count": len(MODULES),
        "layer_count": len(LAYERS),
        "modules": [get_module(m) for m in MODULES],
        "layers": [{"id": lid, **LAYER_CATALOG[lid]} for lid in LAYERS],
        "targets": list(TARGETS),
        "sample_job_id": SAMPLE_JOB_ID,
        "sample_customer": SAMPLE_CUSTOMER,
    }
