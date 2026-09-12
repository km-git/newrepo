"""Module handler registry and job runner."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .constants import MODULES
from .platform import PlatformContext

Handler = Callable[[PlatformContext, dict[str, Any], dict[str, Any]], dict[str, Any]]


def _collect_files(source: str | None) -> tuple[list[Path], Path | None]:
    if not source:
        return [], None
    root = Path(source)
    if not root.exists():
        raise FileNotFoundError(source)
    if root.is_file():
        return [root], root.parent
    files = [p for p in root.rglob("*") if p.is_file()]
    return files, root


def _handler_audit(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    files, _root = _collect_files(params.get("source_path"))
    degradation = min(10, max(1, len(files) // 10 + 1)) if files else 1
    total_bytes = sum(f.stat().st_size for f in files)
    return {
        "audit": {
            "barcode": params.get("barcode", job["id"][:12]),
            "format": params.get("format", "unknown"),
            "file_count": len(files),
            "byte_estimate": total_bytes,
            "degradation_score": degradation,
            "cloud_cost_forecast_usd": round(total_bytes / (1024**4) * 23.0, 4),
            "rfid": params.get("rfid"),
            "photos": params.get("photos", []),
        }
    }


def _handler_analytics(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    objects = ctx.vault.list_objects(params.get("namespace"))
    total_bytes = sum(o.get("size_bytes", 0) for o in objects)
    duplicates = {}
    for obj in objects:
        h = obj.get("sha256")
        if h:
            duplicates[h] = duplicates.get(h, 0) + 1
    dup_count = sum(1 for c in duplicates.values() if c > 1)
    return {
        "analytics": {
            "object_count": len(objects),
            "total_bytes": total_bytes,
            "duplicate_hash_groups": dup_count,
            "pii_scan": "pending" if params.get("scan_pii") else "skipped",
            "legal_hold_count": len(params.get("legal_holds") or []),
        }
    }


def _handler_vtl_cloud(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    return {
        "vtl": {
            "backend": params.get("backend", "seaweedfs"),
            "iscsi_target": params.get("iscsi_target", "iqn.2026.tape-to-cloud.vtl"),
            "slot_count": params.get("slot_count", 1500),
            "worm_enabled": bool(params.get("worm_enabled")),
            "tape_pool": params.get("tape_pool", "glacier"),
        }
    }


def _handler_restore(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    object_id = params.get("object_id")
    if not object_id:
        raise ValueError("restore requires object_id")
    record = ctx.vault.get_object(object_id, params.get("namespace", "default"))
    if record is None:
        raise FileNotFoundError(object_id)
    return {
        "restore": {
            "object_id": object_id,
            "delivery": params.get("delivery", "cloud_staging"),
            "vault_path": record["vault_path"],
            "sha256": record["sha256"],
            "ediscovery_filters": {
                "keywords": params.get("keywords", []),
                "custodians": params.get("custodians", []),
            },
        }
    }


def _handler_disk_ingest(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    source = params.get("source_path")
    if not source:
        raise ValueError("disk-ingest requires source_path")
    root = Path(source)
    stored = []
    if root.is_file():
        stored.append(ctx.vault.store_file(root, namespace=params.get("namespace", "ingest")))
    else:
        for fp in root.rglob("*"):
            if fp.is_file():
                stored.append(ctx.vault.store_file(fp, namespace=params.get("namespace", "ingest")))
    return {"disk_ingest": {"stored_count": len(stored), "objects": stored[:50]}}


def _handler_email_extract(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    fmt = params.get("format", "pst")
    return {
        "email_extract": {
            "format": fmt,
            "formats_supported": ["pst", "edb", "nsf", "mbox"],
            "filters": {
                "user": params.get("user"),
                "date_from": params.get("date_from"),
                "keywords": params.get("keywords", []),
            },
            "virus_quarantine": bool(params.get("virus_scan", True)),
            "status": "queued" if params.get("source_path") else "awaiting_source",
        }
    }


def _handler_email_migrate(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    return {
        "email_migrate": {
            "source": params.get("source", "groupwise"),
            "target": params.get("target", "m365"),
            "dedup": bool(params.get("dedup", True)),
            "mailbox_count": params.get("mailbox_count", 0),
            "plan_id": job["id"],
        }
    }


def _handler_tape_duplicate(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    object_id = params.get("object_id")
    copies = int(params.get("copies", 1))
    if not object_id:
        raise ValueError("tape-duplicate requires object_id")
    record = ctx.vault.get_object(object_id, params.get("namespace", "default"))
    if record is None:
        raise FileNotFoundError(object_id)
    src = ctx.vault.resolve_path(record)
    dupes = []
    for i in range(copies):
        dupes.append(
            ctx.vault.store_file(
                src,
                namespace=params.get("target_namespace", "duplicate"),
                metadata={"source_object_id": object_id, "copy_index": i + 1},
            )
        )
    return {"tape_duplicate": {"source": object_id, "copies": dupes}}


def _handler_media_ingest(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    files, _ = _collect_files(params.get("source_path"))
    return {
        "media_ingest": {
            "file_count": len(files),
            "broadcast_formats": params.get("formats", ["betacam", "vhs", "digibeta", "dvc"]),
            "transcode": params.get("transcode", "proxy"),
            "destination": params.get("destination", "s3"),
        }
    }


def _handler_tape_ops(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    objects = ctx.vault.list_objects()
    return {
        "tape_ops": {
            "inventory_count": len(objects),
            "library_health": params.get("library_health", "unknown"),
            "scheduled_audit": params.get("scheduled_audit", False),
            "barcodes": [o.get("object_id", "")[:12] for o in objects[:20]],
        }
    }


def _handler_tape_saas(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    tenant = params.get("tenant_id", "default")
    return {
        "tape_saas": {
            "tenant_id": tenant,
            "mfa_required": bool(params.get("mfa", True)),
            "file_level_delete": bool(params.get("file_level_delete")),
            "billing_departments": params.get("departments", []),
            "immutable_catalog": True,
        }
    }


def _handler_tape_vault(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    action = params.get("action", "list")
    if action == "store" and params.get("source_path"):
        record = ctx.vault.store_file(
            Path(params["source_path"]),
            namespace=params.get("namespace", "vault"),
        )
        return {"tape_vault": {"action": "store", "object": record}}
    objects = ctx.vault.list_objects(params.get("namespace"))
    return {"tape_vault": {"action": action, "object_count": len(objects), "objects": objects[:50]}}


def _handler_destroy(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    method = params.get("method", "wipe")
    object_id = params.get("object_id")
    destroyed = []
    if object_id:
        ok = ctx.vault.delete_object(object_id, params.get("namespace", "default"), secure=method != "logical")
        destroyed.append({"object_id": object_id, "destroyed": ok})
    cert = {
        "certificate_id": job["id"],
        "method": method,
        "standards": ["NIST-800-88", "IRS-Pub-1075"],
        "destroyed_objects": destroyed,
    }
    return {"destroy": cert}


def _handler_llm_corpus(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    files, _ = _collect_files(params.get("source_path"))
    text_files = [f for f in files if f.suffix.lower() in {".txt", ".md", ".json", ".csv"}]
    total_chars = sum(f.read_text(encoding="utf-8", errors="ignore")[:10000].__len__() for f in text_files[:20])
    return {
        "llm_corpus": {
            "text_file_count": len(text_files),
            "approx_tokens": total_chars // 4,
            "pii_scrub": bool(params.get("pii_scrub", True)),
            "output_format": params.get("format", "rag-jsonl"),
        }
    }


def _handler_ml_enrich(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    return {
        "ml_enrich": {
            "services": params.get("services", ["ocr", "transcribe", "textract"]),
            "tags": params.get("tags", []),
            "status": "queued",
        }
    }


def _handler_monetize(ctx: PlatformContext, job: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    return {
        "monetize": {
            "action": params.get("action", "report"),
            "asset_id": params.get("asset_id"),
            "license_id": params.get("license_id"),
            "note": "use tape_to_cloud.monetize CLI for full license/royalty operations",
        }
    }


_HANDLERS: dict[str, Handler] = {
    "audit": _handler_audit,
    "analytics": _handler_analytics,
    "vtl-cloud": _handler_vtl_cloud,
    "restore": _handler_restore,
    "disk-ingest": _handler_disk_ingest,
    "email-extract": _handler_email_extract,
    "email-migrate": _handler_email_migrate,
    "tape-duplicate": _handler_tape_duplicate,
    "media-ingest": _handler_media_ingest,
    "tape-ops": _handler_tape_ops,
    "tape-saas": _handler_tape_saas,
    "tape-vault": _handler_tape_vault,
    "destroy": _handler_destroy,
    "llm-corpus": _handler_llm_corpus,
    "ml-enrich": _handler_ml_enrich,
    "monetize": _handler_monetize,
}


def module_descriptions() -> dict[str, str]:
    return {
        "audit": "Comprehensive media audit with SHA-256 manifests",
        "analytics": "Archive insight — duplicates, PII, retention",
        "vtl-cloud": "VTL / Tape Gateway virtualization config",
        "restore": "On-demand restore with eDiscovery filters",
        "disk-ingest": "USB/NAS/SAN ingest to vault",
        "email-extract": "PST/EDB/NSF email extraction",
        "email-migrate": "GroupWise/Lotus → M365 migration plan",
        "tape-duplicate": "1-to-N duplication with hash verify",
        "media-ingest": "Broadcast/video digitization pipeline",
        "tape-ops": "Legacy tape inventory and library health",
        "tape-saas": "Nexus tenant portal configuration",
        "tape-vault": "Offsite vault store/list/retrieve",
        "destroy": "Certified media destruction",
        "llm-corpus": "RAG / private-GPT corpus builder",
        "ml-enrich": "AI/ML tagging and enrichment",
        "monetize": "License, access, royalty reporting",
    }


def run_job(ctx: PlatformContext, job_id: str) -> dict[str, Any]:
    from .layers import apply_all_layers

    job = ctx.jobs.get_job(job_id)
    if job is None:
        raise ValueError(f"job not found: {job_id}")
    ctx.jobs.update_job(job_id, status="running")
    params = job["params"]
    module = job["module"]
    handler = _HANDLERS.get(module)
    if handler is None:
        ctx.jobs.update_job(job_id, status="failed", error=f"no handler for {module}")
        return ctx.jobs.get_job(job_id) or job

    try:
        files, root = _collect_files(params.get("source_path"))
        layers = apply_all_layers(
            job_id=job_id,
            module=module,
            files=files,
            root=root,
            manifests_dir=ctx.manifests_dir,
            params=params,
        )
        module_result = handler(ctx, job, params)
        result = {"layers": layers, **module_result}
        ctx.jobs.update_job(
            job_id,
            status="completed",
            result=result,
            layers_applied=[layer["layer"] for layer in layers],
        )
    except Exception as exc:
        ctx.jobs.update_job(job_id, status="failed", error=str(exc))
    return ctx.jobs.get_job(job_id) or job


def submit_and_run(ctx: PlatformContext, module: str, params: dict[str, Any]) -> dict[str, Any]:
    job = ctx.jobs.create_job(module, params)
    return run_job(ctx, job["id"])


def list_modules() -> list[dict[str, str]]:
    desc = module_descriptions()
    return [{"id": m, "description": desc[m]} for m in MODULES if m in desc]
