"""piicatcher-style column-name heuristics (Apache-2.0 idea; no piicatcher import)."""

from __future__ import annotations

import re

from dspm.classification.models import Finding

# Lowercased column name → (type, confidence, recognizer)
COLUMN_MAP: tuple[tuple[str, str, float, str], ...] = (
    ("email", "PII", 0.82, "column:email"),
    ("e_mail", "PII", 0.82, "column:email"),
    ("mail", "PII", 0.6, "column:email"),
    ("phone", "PII", 0.75, "column:phone"),
    ("mobile", "PII", 0.75, "column:phone"),
    ("tfn", "custom", 0.8, "column:au_tfn"),
    ("tax_file", "custom", 0.8, "column:au_tfn"),
    ("abn", "custom", 0.8, "column:au_abn"),
    ("nhs", "PHI", 0.8, "column:nhs_number"),
    ("ssn", "PII", 0.88, "column:ssn"),
    ("social_security", "PII", 0.88, "column:ssn"),
    ("credit", "PCI", 0.72, "column:pan"),
    ("card", "PCI", 0.68, "column:pan"),
    ("pan", "PCI", 0.8, "column:pan"),
    ("password", "secret", 0.9, "column:secret"),
    ("secret", "secret", 0.85, "column:secret"),
    ("api_key", "secret", 0.9, "column:secret"),
    ("ip", "IP", 0.7, "column:ip"),
    ("address", "PII", 0.65, "column:address"),
    ("dob", "PII", 0.78, "column:dob"),
    ("date_of_birth", "PII", 0.8, "column:dob"),
)

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

_NORM = re.compile(r"[^a-z0-9]+")


def normalize_column(name: str) -> str:
    return _NORM.sub("_", (name or "").strip().lower()).strip("_")


def classify_columns(columns: list[str], *, source: str) -> list[Finding]:
    """Flag schema-level PII from column names even when cell values are empty."""
    found: list[Finding] = []
    seen: set[str] = set()
    for col in columns:
        key = normalize_column(col)
        if not key or key in seen:
            continue
        for needle, ftype, conf, recognizer in COLUMN_MAP:
            if needle == key or needle in key.split("_") or key.startswith(needle):
                seen.add(key)
                found.append(
                    Finding(
                        source=source,
                        location=f"{col}:schema",
                        type=ftype,
                        confidence=conf,
                        verdict=VERDICT.get(ftype, "internal"),
                        suggested_action=SUGGESTED.get(ftype, "review"),
                        recognizer=recognizer,
                        value_preview=col,
                    )
                )
                break
    return found
