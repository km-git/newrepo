"""Classification — Presidio + regex fallback for PII/PHI/PCI detection."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from dspm.models import Finding

# Regex patterns for offline classification (no spaCy model required)
PATTERNS: list[tuple[str, str, float, str]] = [
    ("EMAIL", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", 0.95, "PII"),
    ("PHONE", r"\+?1?\d{10,12}", 0.85, "PII"),
    ("CREDIT_CARD", r"\b(?:\d[ -]*?){13,16}\b", 0.90, "PCI"),
    ("SSN", r"\b\d{3}-\d{2}-\d{4}\b", 0.92, "PII"),
    ("IP_ADDRESS", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 0.88, "IP"),
    ("AWS_KEY", r"AKIA[0-9A-Z]{16}", 0.99, "secret"),
    ("NHS", r"\b\d{3}\s?\d{3}\s?\d{4}\b", 0.87, "PHI"),
    ("AU_TFN", r"\b\d{3}\s?\d{3}\s?\d{3}\b", 0.80, "custom"),
    ("AU_ABN", r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b", 0.82, "custom"),
]

PRESCRIPTION_KEYWORDS = {"rx", "prescription", "medication", "diagnosis", "patient"}


def _try_presidio(text: str, location: str, source: str) -> list[Finding]:
    try:
        from presidio_analyzer import AnalyzerEngine

        engine = AnalyzerEngine()
        results = engine.analyze(text=text, language="en")
        findings: list[Finding] = []
        for r in results:
            findings.append(
                Finding(
                    source=source,
                    location=location,
                    type=r.entity_type,
                    confidence=float(r.score),
                    verdict="PII" if r.entity_type in {"EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN"} else "sensitive",
                    suggested_action="mask or restrict access",
                )
            )
        return findings
    except Exception:
        return []


def classify_text(text: str, location: str, source: str, use_presidio: bool = False) -> list[Finding]:
    if use_presidio:
        findings = _try_presidio(text, location, source)
        if findings:
            return findings
    results: list[Finding] = []
    for name, pattern, score, ftype in PATTERNS:
        if re.search(pattern, text):
            verdict = "PII" if ftype in {"PII", "PHI", "PCI"} else ftype
            if ftype == "secret":
                verdict = "sensitive"
            results.append(
                Finding(
                    source=source,
                    location=location,
                    type=ftype if ftype != "custom" else name,
                    confidence=score,
                    verdict=verdict,
                    suggested_action="mask or restrict access",
                )
            )
    lower = text.lower()
    if any(kw in lower for kw in PRESCRIPTION_KEYWORDS):
        results.append(
            Finding(
                source=source,
                location=location,
                type="PHI",
                confidence=0.75,
                verdict="sensitive",
                suggested_action="encrypt at rest",
            )
        )
    return results


def classify_csv(path: Path, max_rows: int = 100, use_presidio: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            for col, val in row.items():
                if not val or not str(val).strip():
                    continue
                findings.extend(classify_text(str(val), col, str(path), use_presidio=use_presidio))
    return findings


def findings_to_dict(findings: list[Finding]) -> list[dict]:
    return [f.model_dump() for f in findings]
