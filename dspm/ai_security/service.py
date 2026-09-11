"""Experimental vector-store / prompt-log scanner. Not a product."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dspm.ai_security.models import AiFinding
from dspm.classification.service import analyze_text
from dspm.db.store import FindingsStore, utcnow

EXPERIMENTAL = "experimental: 200-line vector-store scanner, not a Cyera-equivalent AI-workload product"


def scan_export(path: str | Path, *, store: FindingsStore | None = None) -> list[AiFinding]:
    target = Path(path)
    rows: list[dict[str, Any]]
    if target.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        payload = json.loads(target.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else [payload]
    found: list[AiFinding] = []
    for idx, row in enumerate(rows):
        text = str(row.get("prompt") or row.get("text") or row.get("document") or json.dumps(row))
        for hit in analyze_text(text, column="prompt", source=str(target)):
            found.append(
                AiFinding(
                    store=str(target),
                    location=f"record:{idx}:{hit.location}",
                    type=hit.type,
                    confidence=hit.confidence,
                    warning=EXPERIMENTAL,
                    extra={"verdict": hit.verdict, "recognizer": hit.recognizer},
                )
            )
    if store is not None:
        for item in found:
            store.insert(
                "findings_ai_security",
                {
                    "store": item.store,
                    "location": item.location,
                    "type": item.type,
                    "confidence": item.confidence,
                    "extra": item.extra,
                    "scanned_at": utcnow(),
                },
            )
    return found


def scan_vectorstore_uri(uri: str) -> dict[str, Any]:
    return {
        "uri": uri,
        "status": "stub",
        "warning": EXPERIMENTAL,
        "hint": "export pgvector/Chroma/Weaviate/Pinecone to JSON/JSONL and run dspm ai-security scan-export",
    }
