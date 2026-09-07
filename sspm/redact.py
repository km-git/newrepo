"""PII scrub for report output. Presidio when installed; regex fallback otherwise."""

from __future__ import annotations

import re
from typing import Any

from sspm.constants import PRESIDIO_SOURCE

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._+-]{1,64}@[A-Za-z0-9.-]{1,255}\.[A-Za-z]{2,24}",
    re.I,
)
TENANT_ID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.I,
)


def scrub_text(text: str) -> str:
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
    except ImportError:
        cleaned = EMAIL_RE.sub("[REDACTED-EMAIL]", text)
        return TENANT_ID_RE.sub("[REDACTED-ID]", cleaned)
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    results = analyzer.analyze(text=text, language="en")
    return anonymizer.anonymize(text=text, analyzer_results=results).text


def scrub_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return scrub_text(payload)
    if isinstance(payload, list):
        return [scrub_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {k: scrub_payload(v) for k, v in payload.items()}
    return payload


def presidio_source() -> str:
    return PRESIDIO_SOURCE
