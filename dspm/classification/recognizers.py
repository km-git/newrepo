"""Presidio-compatible pattern recognizers (stdlib). Optional Presidio adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from dspm.constants import PRESIDIO_SOURCE

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")
AU_PHONE_RE = re.compile(r"\b(?:\+?61|0)[2-478](?:[ -]?\d){8}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
# ATO-style TFN: 8 or 9 digits, optional spaces.
TFN_RE = re.compile(r"\b\d{3}[ -]?\d{3}[ -]?\d{2,3}\b")
ABN_RE = re.compile(r"\b\d{2}[ ]?\d{3}[ ]?\d{3}[ ]?\d{3}\b")
NHS_RE = re.compile(r"\b\d{3}[ -]?\d{3}[ -]?\d{4}\b")


@dataclass
class Pattern:
    name: str
    regex: str
    score: float


@dataclass
class Match:
    type: str
    value: str
    start: int
    end: int
    score: float
    recognizer: str
    context: list[str] = field(default_factory=list)


@dataclass
class PatternRecognizer:
    """Mirrors Presidio PatternRecognizer without requiring the package at test time."""

    name: str
    patterns: list[Pattern]
    context_words: list[str]
    score_threshold: float
    finding_type: str
    compiled: list[tuple[Pattern, re.Pattern[str]]] = field(init=False)

    def __post_init__(self) -> None:
        self.compiled = [(p, re.compile(p.regex, re.I)) for p in self.patterns]

    def analyze(self, text: str, *, column: str = "") -> list[Match]:
        hay = f"{column} {text}"
        lowered = hay.lower()
        ctx_hit = any(word.lower() in lowered for word in self.context_words) if self.context_words else True
        found: list[Match] = []
        for pattern, cre in self.compiled:
            for match in cre.finditer(text):
                score = pattern.score if ctx_hit else max(0.0, pattern.score - 0.2)
                if score < self.score_threshold:
                    continue
                found.append(
                    Match(
                        type=self.finding_type,
                        value=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        score=round(min(1.0, score), 3),
                        recognizer=self.name,
                        context=self.context_words,
                    )
                )
        return found


def luhn_ok(num: str) -> bool:
    digits = [int(ch) for ch in re.sub(r"\D", "", num)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def builtin_recognizers() -> list[PatternRecognizer]:
    return [
        PatternRecognizer(
            name="email",
            patterns=[Pattern("email", EMAIL_RE.pattern, 0.9)],
            context_words=["email", "mail", "contact"],
            score_threshold=0.5,
            finding_type="PII",
        ),
        PatternRecognizer(
            name="au_phone",
            patterns=[Pattern("au_phone", AU_PHONE_RE.pattern, 0.7)],
            context_words=["phone", "mobile", "tel"],
            score_threshold=0.4,
            finding_type="PII",
        ),
        PatternRecognizer(
            name="ipv4",
            patterns=[Pattern("ipv4", IPV4_RE.pattern, 0.6)],
            context_words=["ip", "host", "addr"],
            score_threshold=0.3,
            finding_type="IP",
        ),
        PatternRecognizer(
            name="aws_access_key",
            patterns=[Pattern("aws_key", AWS_KEY_RE.pattern, 0.95)],
            context_words=["aws", "key", "secret", "access"],
            score_threshold=0.5,
            finding_type="secret",
        ),
    ]


def try_presidio() -> dict[str, Any]:
    """Optional adapter. Official source is data-privacy-stack/presidio (moved 2026)."""
    try:
        import presidio_analyzer  # type: ignore[import-not-found]
    except ImportError:
        return {
            "available": False,
            "source": PRESIDIO_SOURCE,
            "reason": "presidio-analyzer not installed; using stdlib recognizers",
        }
    return {
        "available": True,
        "source": PRESIDIO_SOURCE,
        "module": getattr(presidio_analyzer, "__file__", ""),
    }
