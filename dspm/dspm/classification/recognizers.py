"""Custom Presidio recognizers for AU TFN, AU ABN, NHS."""

from __future__ import annotations

import re

CUSTOM_TYPES = {
    "au_tfn": {
        "pattern": r"\b\d{3}\s?\d{3}\s?\d{3}\b",
        "context_words": ["tfn", "tax file", "australian tax"],
        "score_threshold": 0.7,
    },
    "au_abn": {
        "pattern": r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b",
        "context_words": ["abn", "business number", "australian business"],
        "score_threshold": 0.75,
    },
    "nhs_number": {
        "pattern": r"\b\d{3}\s?\d{3}\s?\d{4}\b",
        "context_words": ["nhs", "national health", "patient id"],
        "score_threshold": 0.8,
    },
}


def check_custom_type(type_name: str, text: str) -> dict:
    cfg = CUSTOM_TYPES.get(type_name)
    if not cfg:
        return {"match": False, "error": f"unknown type {type_name}"}
    matched = bool(re.search(cfg["pattern"], text))
    context_hit = any(w in text.lower() for w in cfg["context_words"])
    score = cfg["score_threshold"] if matched else 0.0
    if matched and context_hit:
        score = min(1.0, score + 0.1)
    return {
        "type": type_name,
        "match": matched,
        "score": score,
        "meets_threshold": score >= cfg["score_threshold"],
    }
