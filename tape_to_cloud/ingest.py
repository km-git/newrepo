"""Disk ingest: copy real bytes, pre/post SHA-256, CoC, optional WORM + email extract.

This is the working MVP for `disk-ingest` + `integrity` + `ediscovery` (.eml/.mbox) + `worm`.
It does not drive LTO hardware. `.enc` files without `--unwrap-key` are refused (no crypto bypass).
"""

from __future__ import annotations

import json
import tarfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tape_to_cloud.coc import append_event, load_events
from tape_to_cloud.email_extract import extract_email_tree
from tape_to_cloud.ids import resolved_job_dir
from tape_to_cloud.integrity import HASH_ALG, REFUSED, canonical_sha256, sha256_file
from tape_to_cloud.store import default_store, delete_object, get_file, object_path, put_file
from tape_to_cloud.worm import apply_lock, load_lock


def _job_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"job-{stamp}-{uuid.uuid4().hex[:8]}"


def _iter_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    return sorted(p for p in source.rglob("*") if p.is_file())


def _tar_listing(path: Path) -> list[str] | None:
    if path.suffix.lower() not in {".tar", ".tgz"} and not path.name.endswith(".tar.gz"):
        return None
    names: list[str] = []
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            names.append(member.name)
    return names


def ingest(
    source: Path,
    *,
    store: Path | None = None,
    matter_id: str = "UNTITLED",
    keyword: str | None = None,
    worm_until: str | None = None,
    unwrap_key: Path | None = None,
) -> dict[str, Any]:
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    store = (store or default_store()).resolve()
    job_id = _job_id()
    job_dir = store / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    coc = job_dir / "coc.jsonl"
    append_event(coc, "job_open", job_id=job_id, matter_id=matter_id, source=str(source))

    objects: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for path in _iter_files(source):
        rel = str(path.relative_to(source) if source.is_dir() else path.name)
        if path.suffix.lower() == ".enc" and unwrap_key is None:
            append_event(coc, "refuse_encrypted_without_keys", path=rel, action="STOP_AND_ASK")
            failures.append({"path": rel, "error": "encrypted-without-keys", "action": "STOP_AND_ASK"})
            continue
        pre = sha256_file(path)
        append_event(coc, "pre_sha256", path=rel, sha256=pre, alg=HASH_ALG)
        try:
            digest, dest = put_file(store, path, expected_sha256=pre)
        except ValueError as exc:
            failures.append({"path": rel, "error": str(exc)})
            append_event(coc, "copy_fail", path=rel, error=str(exc))
            continue
        append_event(coc, "post_sha256_match", path=rel, sha256=digest, object=str(dest))
        rec: dict[str, Any] = {
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": digest,
            "stored": str(dest),
            "match": True,
            "opaque_ciphertext": path.suffix.lower() == ".enc",
        }
        if unwrap_key is not None and path.suffix.lower() == ".enc":
            rec["unwrap_key_sha256"] = sha256_file(unwrap_key)
        listing = _tar_listing(path)
        if listing is not None:
            rec["format_reader"] = "tarfile"
            rec["tar_members"] = listing[:200]
        objects.append(rec)

    email_hits = extract_email_tree(source if source.is_dir() else source.parent, keyword=keyword)
    if email_hits:
        (job_dir / "email_production.json").write_text(
            json.dumps(email_hits, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        append_event(coc, "email_extract", hits=len(email_hits), keyword=keyword)

    worm = apply_lock(job_dir, until_utc=worm_until) if worm_until else None
    if worm:
        append_event(coc, "worm_lock", **worm)

    report: dict[str, Any] = {
        "id": job_id,
        "kind": "live_ingest",
        "sample": False,
        "title": f"Live ingest {job_id}",
        "generated_utc": datetime.now(UTC).isoformat(),
        "matter_id": matter_id,
        "status": "complete" if objects and not failures else ("failed" if not objects else "partial"),
        "modules": ["disk-ingest", "restore", "email-extract"],
        "layers": ["integrity", "ediscovery", "worm", "format-readers", "kms-kmip", "media-rescue"],
        "hash_algorithm": HASH_ALG,
        "refused_hash_algorithms": list(REFUSED),
        "source": str(source),
        "store": str(store),
        "object_count": len(objects),
        "bytes": sum(o["bytes"] for o in objects),
        "objects": objects,
        "failures": failures,
        "email_hits": len(email_hits),
        "worm": worm,
        "coc_events": len(load_events(coc)),
    }
    report["canonical_sha256"] = canonical_sha256(report)
    (job_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    append_event(coc, "job_complete", job_id=job_id, objects=len(objects), failures=len(failures))
    return report


def _safe_relpath(raw: str) -> Path:
    rel = Path(raw)
    if rel.is_absolute() or any(part == ".." for part in rel.parts):
        raise ValueError(f"unsafe restore path: {raw}")
    return rel


def restore_job(job_id: str, dest: Path, *, store: Path | None = None) -> dict[str, Any]:
    store = (store or default_store()).resolve()
    job_dir = resolved_job_dir(store, job_id)
    report_path = job_dir / "report.json"
    if not report_path.is_file():
        raise FileNotFoundError(job_id)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    restored = []
    for obj in report.get("objects") or []:
        out = dest / _safe_relpath(str(obj["path"]))
        get_file(store, obj["sha256"], out)
        restored.append({"path": str(out), "sha256": sha256_file(out), "match": True})
    append_event(job_dir / "coc.jsonl", "restore", dest=str(dest), count=len(restored))
    return {"job_id": job_id, "restored": restored}


def verify_job(job_id: str, *, store: Path | None = None) -> dict[str, Any]:
    store = (store or default_store()).resolve()
    job_dir = resolved_job_dir(store, job_id)
    report = json.loads((job_dir / "report.json").read_text(encoding="utf-8"))
    mismatches = []
    for obj in report.get("objects") or []:
        try:
            path = object_path(store, obj["sha256"])
        except ValueError:
            mismatches.append(obj["sha256"])
            continue
        if not path.is_file() or sha256_file(path) != obj["sha256"]:
            mismatches.append(obj["sha256"])
    recomputed = canonical_sha256(report)
    return {
        "job_id": job_id,
        "objects_ok": not mismatches,
        "mismatches": mismatches,
        "report_hash_ok": recomputed == report.get("canonical_sha256"),
        "worm": load_lock(job_dir),
    }


def try_delete_job_object(job_id: str, digest: str, *, store: Path | None = None) -> None:
    store = (store or default_store()).resolve()
    delete_object(store, digest, resolved_job_dir(store, job_id))


__all__ = [
    "default_store",
    "ingest",
    "restore_job",
    "try_delete_job_object",
    "verify_job",
]
