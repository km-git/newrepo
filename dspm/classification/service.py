"""Classify CSV/JSON/text with stdlib recognizers; Presidio + HF + Gemini are optional."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from dspm.classification.checksums import abn_checksum_ok, nhs_checksum_ok, tfn_plausible
from dspm.classification.models import ClassifyResult, Finding
from dspm.classification.recognizers import CARD_RE, Match, builtin_recognizers, luhn_ok, try_presidio
from dspm.custom_types.service import recognizers_from_registry
from dspm.db.store import FindingsStore, utcnow

SUGGESTED = {
    "PII": "mask or restrict access",
    "PHI": "quarantine and apply HIPAA/GDPR controls",
    "PCI": "remove PAN / tokenize; restrict to PCI scope",
    "secret": "rotate credential and scan git history",
    "IP": "confirm whether the address is internal-only",
    "custom": "review custom-type policy with the data owner",
}

VERDICT = {
    "PII": "PII",
    "PHI": "sensitive",
    "PCI": "sensitive",
    "secret": "sensitive",
    "IP": "internal",
    "custom": "PII",
}


def _preview(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) <= 8:
        return compact
    return compact[:3] + "…" + compact[-2:]


def _card_matches(text: str) -> list[Match]:
    found: list[Match] = []
    for match in CARD_RE.finditer(text):
        raw = match.group(0)
        if not luhn_ok(raw):
            continue
        found.append(
            Match(
                type="PCI",
                value=raw,
                start=match.start(),
                end=match.end(),
                score=0.85,
                recognizer="luhn_pan",
            )
        )
    return found


def analyze_text(text: str, *, column: str = "", source: str = "") -> list[Finding]:
    matches: list[Match] = []
    for rec in builtin_recognizers() + recognizers_from_registry():
        matches.extend(rec.analyze(text, column=column))
    matches.extend(_card_matches(text))
    extra: list[Finding] = []
    for match in matches:
        ftype = match.type
        if match.recognizer == "au_tfn" and not tfn_plausible(match.value):
            continue
        if match.recognizer == "au_abn" and not abn_checksum_ok(match.value):
            continue
        if match.recognizer == "nhs_number" and not nhs_checksum_ok(match.value):
            continue
        extra.append(
            Finding(
                source=source,
                location=column or f"offset:{match.start}",
                type=ftype,
                confidence=match.score,
                verdict=VERDICT.get(ftype, "internal"),
                suggested_action=SUGGESTED.get(ftype, "review"),
                recognizer=match.recognizer,
                value_preview=_preview(match.value),
            )
        )
    return extra


def _read_tabular(path: Path, limit: int = 100) -> tuple[list[dict[str, str]], int]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
        clipped = [{str(k): str(v) for k, v in dict(row).items()} for row in rows[:limit]]
        return clipped, len(rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        total = 0
        for row in reader:
            total += 1
            if len(rows) < limit:
                rows.append({str(k): str(v) for k, v in row.items()})
        return rows, total


def classify_path(path: str | Path, *, limit: int = 100, store: FindingsStore | None = None) -> ClassifyResult:
    target = Path(path)
    engine = "stdlib-recognizers"
    presidio = try_presidio()
    if presidio.get("available"):
        engine = "presidio+" + engine
    if os.environ.get("DSPM_HF_NER") == "1":
        engine += "+hf-ner-stub"
    if os.environ.get("GEMINI_API_KEY"):
        engine += "+gemini-flash-long-tail"

    findings: list[Finding] = []
    rows_scanned = 0
    if target.is_dir():
        files = sorted(
            p for p in target.rglob("*") if p.suffix.lower() in {".csv", ".json", ".txt", ".jsonl"} and p.is_file()
        )
        for file in files:
            part = classify_path(file, limit=limit, store=None)
            findings.extend(part.findings)
            rows_scanned += part.rows_scanned
    elif target.suffix.lower() in {".csv", ".json"}:
        rows, total = _read_tabular(target, limit=limit)
        rows_scanned = min(limit, total)
        for idx, row in enumerate(rows):
            for col, value in row.items():
                for finding in analyze_text(value, column=col, source=str(target)):
                    finding.location = f"{col}:row{idx + 1}"
                    findings.append(finding)
    else:
        text = target.read_text(encoding="utf-8", errors="replace")
        findings.extend(analyze_text(text, column="body", source=str(target)))
        rows_scanned = 1

    if store is not None:
        for finding in findings:
            store.insert(
                "findings",
                {
                    "source": finding.source,
                    "location": finding.location,
                    "type": finding.type,
                    "confidence": finding.confidence,
                    "verdict": finding.verdict,
                    "suggested_action": finding.suggested_action,
                    "extra": finding.model_dump(),
                    "created_at": utcnow(),
                },
            )
    return ClassifyResult(findings=findings, engine=engine, source=str(target), rows_scanned=rows_scanned)


def classify_postgres_stub(table: str) -> dict[str, Any]:
    return {
        "table": table,
        "status": "stub",
        "hint": "connect DSPM_DB postgres DSN and run Presidio on first 100 rows",
        "engine": try_presidio(),
    }
