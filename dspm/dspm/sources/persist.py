"""Persist source scan results."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from dspm.sources.models import SourceScanResult
from dspm.store.db import init_db, insert_row, persist_scan_results


def save_source_scan(result: SourceScanResult) -> dict:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    scan_id = insert_row(
        "source_scans",
        {
            "source_uri": result.source_uri,
            "provider": result.provider,
            "object_count": result.object_count,
            "finding_count": len(result.findings),
            "created_at": now,
        },
    )
    for obj in result.objects[:500]:
        insert_row(
            "source_objects",
            {
                "source_uri": result.source_uri,
                "path": obj.path,
                "name": obj.name,
                "provider": obj.provider,
                "store_type": obj.store_type,
                "size_bytes": obj.size_bytes,
                "metadata": json.dumps(obj.metadata),
                "created_at": now,
            },
        )
    if result.findings:
        persist_scan_results(result.findings)
    return {"scan_id": scan_id, "object_count": result.object_count, "finding_count": len(result.findings)}
