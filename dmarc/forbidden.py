"""Strip disallowed attestation language from operator-facing reports."""

from __future__ import annotations

import re

FORBIDDEN = (
    "compliance",
    "attestation",
    "certified",
    "secure",
    "guaranteed",
    "guarantees",
)

_REPLACEMENTS = {
    "compliance": "deliverability observation",
    "attestation": "authentication reference",
    "certified": "observed",
    "secure": "authenticated",
    "guaranteed": "expected",
    "guarantees": "observations",
}

_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in FORBIDDEN) + r")\b",
    re.IGNORECASE,
)


def contains_forbidden(text: str) -> bool:
    return bool(_PATTERN.search(text or ""))


def sanitize_report_text(text: str) -> str:
    """Replace banned words; keep surrounding sentence structure."""

    def _sub(match: re.Match[str]) -> str:
        word = match.group(1).lower()
        return _REPLACEMENTS.get(word, "observation")

    return _PATTERN.sub(_sub, text or "")
