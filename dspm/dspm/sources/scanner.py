"""Scan sources: discover objects, preview content, classify unstructured data."""

from __future__ import annotations

from dspm.classification.service import classify_text
from dspm.sources.models import SourceScanResult


def scan_source(uri: str, max_objects: int = 200, classify_limit: int = 50) -> SourceScanResult:
    from dspm.sources.registry import discover, preview

    objects = discover(uri, max_objects=max_objects)
    scheme = uri.split("://")[0] if "://" in uri else "file"
    findings: list[dict] = []
    classified = 0
    for obj in objects:
        if classified >= classify_limit:
            break
        if not _is_classifiable(obj):
            continue
        prev = preview(uri, obj.path, max_bytes=4096)
        if not prev.preview_text.strip():
            continue
        text_findings = classify_text(prev.preview_text, obj.path, uri)
        for f in text_findings:
            finding_dict = f.model_dump()
            finding_dict["object_name"] = obj.name
            finding_dict["provider"] = obj.provider
            findings.append(finding_dict)
        classified += 1
    return SourceScanResult(
        source_uri=uri,
        provider=scheme,
        objects=objects,
        object_count=len(objects),
        findings=findings,
    )


def _is_classifiable(obj) -> bool:
    text_types = {
        "file",
        "object",
        "archive_member",
        "sharepoint_file",
        "onedrive_file",
        "mailbox_message",
        "unstructured",
    }
    text_ext = {".csv", ".txt", ".json", ".xml", ".html", ".log", ".eml", ".md"}
    if obj.store_type in text_types:
        return True
    if any(obj.name.lower().endswith(ext) for ext in text_ext):
        return True
    return obj.store_type in {"file", "object"}
