"""Deterministic demo reports for every tape-to-cloud module and layer."""

from __future__ import annotations

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

_RESULTS: dict[str, dict[str, Any]] = {
    "audit": {
        "tapes": [
            {
                "barcode": "LTO7-ACME-00421",
                "qr": "t2c://acme/LTO7-ACME-00421",
                "rfid_mam": "IBM-LTO7-MAM-8C2F",
                "format": "LTO-7 LTFS + TSM",
                "bytes_estimate": 5_497_558_138_880,
                "degradation": 3,
                "header_sha256": "9f2c" + "a" * 60,
                "photos_360": 12,
                "files_sampled": 1842,
                "cloud_cost_forecast_usd": 128.40,
            },
            {
                "barcode": "3592-JAG-00088",
                "qr": "t2c://acme/3592-JAG-00088",
                "rfid_mam": "IBM-3592-E08",
                "format": "IBM 3592 Jaguar / TSM",
                "bytes_estimate": 10_000_000_000_000,
                "degradation": 6,
                "header_sha256": "11ab" + "b" * 60,
                "photos_360": 12,
                "files_sampled": 410,
                "cloud_cost_forecast_usd": 310.00,
            },
        ],
        "fleet_note": "LTO-10 present elsewhere in this library; no LTO-10 backward read — mixed drives required.",
    },
    "analytics": {
        "objects": 1_204_331,
        "duplicate_bytes": 88_123_000_000,
        "pii_hits": {"email": 1204, "pan": 12, "ssn": 0},
        "mixed_retention_tapes": 7,
        "legal_holds": ["HOLD-2024-0118"],
        "orphan_catalogs": 2,
        "oldest_object_utc": "1998-04-12T00:00:00+00:00",
    },
    "vtl-cloud": {
        "vtl": "seaweedfs-vtl-01",
        "iscsi_target": "iqn.2026-09.com.acme:vtl-01",
        "slots": 1500,
        "lifecycle": "Glacier Flexible after 30d; Deep Archive after 180d",
        "worm": "S3 Object Lock COMPLIANCE 2557d",
        "presented_to": ["IBM Spectrum Protect", "Cohesity DataProtect"],
    },
    "restore": {
        "mode": "file-extract",
        "filters": {"custodian": "j.lee", "date_from": "2014-01-01", "keyword": "well-log"},
        "objects_restored": 318,
        "bytes": 42_001_992,
        "delivery": "s3://acme-restore/job-demo/ + encrypted USB option",
        "bit_image": False,
    },
    "disk-ingest": {
        "media": ["USB-HDD-4TB", "NAS-nfs://vault/proj", "Snowball-EDGE-01"],
        "bytes_ingested": 3_221_225_472_000,
        "hdd_rescue": {"attempted": True, "recovered_pct": 97.4, "stopped_for_keys": False},
        "manifest_sha256": "c0de" + "c" * 60,
    },
    "email-extract": {
        "stores": ["EDB", "PST", "NSF"],
        "mailboxes": 86,
        "messages": 1_104_220,
        "quarantine_virus": 14,
        "ediscovery_hits": 209,
        "custodians": ["j.lee", "r.okonkwo", "legal-hold-box"],
    },
    "email-migrate": {
        "source": "GroupWise + Exchange 2010",
        "target": "Microsoft 365",
        "mailboxes_migrated": 86,
        "dedup_removed": 190_441,
        "ncp_retirement": "scheduled",
        "workspace_also": False,
    },
    "tape-duplicate": {
        "source": "LTO7-ACME-00421",
        "targets": ["LTO7-COPY-A", "LTO7-COPY-B"],
        "path": "seismic/SEG-Y",
        "verified": True,
        "signed_manifest": "manifests/LTO7-ACME-00421.dup.sha256.json",
    },
    "media-ingest": {
        "items": [
            {"id": "BETACAM-SP-019", "proxy": "h264-720p", "duration_s": 1920},
            {"id": "DICOM-STUDY-77", "proxy": "jpeg-series", "frames": 240},
        ],
        "pipeline": "mediainfo + ffmpeg + Media2Cloud",
        "target_prefix": "s3://acme-media/proxies/",
    },
    "tape-ops": {
        "library": "IBM TS4500",
        "drives": {"healthy": 11, "degraded": 1, "down": 0},
        "robotics": "mtx ok",
        "onsite_mobilization": "crew window 2026-09-14",
        "next_scheduled_audit": "2026-09-21T09:00:00+10:00",
    },
    "tape-saas": {
        "tenant": "acme-energy",
        "users": 42,
        "mfa": True,
        "file_level_dispose": {"eligible": 1204, "blocked_by_hold": 88},
        "dept_billing": {"exploration": 8120.15, "legal": 440.00},
        "immutable_catalog": True,
    },
    "tape-vault": {
        "residual_cartridges": 310,
        "vault": "offsite-BNE-02",
        "courier_coc": "COC-2026-0907-441",
        "dr_rto_hours": 4,
        "library_move": None,
    },
    "destroy": {
        "method": "degauss + shred",
        "standard": "NIST 800-88 Rev. 1 + IRS Pub 1075",
        "items": 12,
        "certificate_id": "ITAD-CERT-2026-0907-12",
        "hold_blocked": 0,
    },
    "llm-corpus": {
        "files_in": 1842,
        "after_dedup": 1510,
        "pii_scrubbed": True,
        "tokens": 12_400_000,
        "format": "Dolma-like JSONL shards",
        "output_prefix": "s3://acme-llm/corpus/job-demo/",
    },
    "ml-enrich": {
        "ocr_pages": 4401,
        "transcribe_hours": 18.5,
        "dicom_studies": 7,
        "seg_traces": 22,
        "labels": ["well-log", "contract", "seismic-line"],
    },
    "monetize": {
        "license_class": "internal-research",
        "assets_tagged": 1510,
        "access_policy": "s3://acme-policies/job-demo.json",
        "royalty_period": "2026-09",
        "royalty_usd": 0.0,
        "note": "Demo customer; royalties accrue only on third-party reuse.",
    },
}


def _layer_block(module_id: str) -> dict[str, Any]:
    return {
        "integrity": {
            "algo": "SHA-256",
            "pre_hash": "aa" * 32,
            "post_hash": "bb" * 32,
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
            "policy": "S3 Object Lock COMPLIANCE",
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
    return {
        "report_id": spec["sample_report_id"],
        "kind": "sample",
        "disclaimer": "Synthetic demo data. Not a customer record.",
        "generated_utc": SAMPLE_GENERATED_UTC,
        "job_id": SAMPLE_JOB_ID,
        "customer": SAMPLE_CUSTOMER,
        "module": module_id,
        "menu": spec["menu"],
        "deliverable": spec["deliverable"],
        "layers_called": dict(LAYERS_CALLED),
        "layers": _layer_block(module_id),
        "result": _RESULTS[module_id],
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
        "module_count": len(reports),
        "layer_count": len(LAYERS),
        "modules": [r["module"] for r in reports],
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
