"""PII scrub for report output. Presidio when installed; split fallback otherwise."""

from __future__ import annotations

from typing import Any

from sspm.constants import PRESIDIO_SOURCE

_EMAIL_BREAKS = frozenset(" \t\n\r<>()[],;:\"'")


def looks_like_email(text: str) -> bool:
    if text.count("@") != 1:
        return False
    local, domain = text.split("@", 1)
    if not local or not domain or "." not in domain:
        return False
    if len(local) > 64 or len(domain) > 255:
        return False
    return " " not in text


def _redact_emails(text: str) -> str:
    pieces: list[str] = []
    start = 0
    while True:
        at = text.find("@", start)
        if at < 0:
            pieces.append(text[start:])
            break
        left = at
        while left > start and text[left - 1] not in _EMAIL_BREAKS:
            left -= 1
            if at - left > 64:
                left = at - 64
                break
        right = at + 1
        limit = min(len(text), at + 1 + 255)
        while right < limit and text[right] not in _EMAIL_BREAKS:
            right += 1
        candidate = text[left:right]
        if looks_like_email(candidate):
            pieces.append(text[start:left])
            pieces.append("[REDACTED-EMAIL]")
            start = right
        else:
            pieces.append(text[start : at + 1])
            start = at + 1
    return "".join(pieces)


def _redact_tenant_ids(text: str) -> str:
    hexdigits = "0123456789abcdefABCDEF"
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if (
            i + 36 <= n
            and text[i + 8] == "-"
            and text[i + 13] == "-"
            and text[i + 18] == "-"
            and text[i + 23] == "-"
            and all(
                ch in hexdigits
                for ch in text[i : i + 8]
                + text[i + 9 : i + 13]
                + text[i + 14 : i + 18]
                + text[i + 19 : i + 23]
                + text[i + 24 : i + 36]
            )
            and (i == 0 or not text[i - 1].isalnum())
            and (i + 36 == n or not text[i + 36].isalnum())
        ):
            out.append("[REDACTED-ID]")
            i += 36
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def scrub_text(text: str) -> str:
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
    except ImportError:
        return _redact_tenant_ids(_redact_emails(text))
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
