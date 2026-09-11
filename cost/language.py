"""Report-language guard. This is a cost and configuration review, not an attestation."""

from __future__ import annotations

import re

BANNED = (
    "compliance",
    "attestation",
    "certified",
    "secure",
    "guaranteed",
    "guarantees",
)

REPLACEMENTS = {
    "compliance": "framework reference",
    "attestation": "configuration reference",
    "certified": "mapped",
    "secure": "configured",
    "guaranteed": "estimated",
    "guarantees": "estimates",
}

_BANNED_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in BANNED) + r")\b",
    re.IGNORECASE,
)


def contains_banned(text: str) -> list[str]:
    found = {m.group(1).lower() for m in _BANNED_RE.finditer(text or "")}
    return sorted(found)


def scrub_report_text(text: str) -> str:
    """Replace banned tokens in report output. Module/file names are not rewritten."""

    def _sub(match: re.Match[str]) -> str:
        word = match.group(1).lower()
        return REPLACEMENTS.get(word, "cost observation")

    return _BANNED_RE.sub(_sub, text or "")


def assert_report_language(text: str) -> None:
    hits = contains_banned(text)
    if hits:
        raise ValueError(f"disallowed report language: {', '.join(hits)}")
