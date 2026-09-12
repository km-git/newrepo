"""AI workload / vector-store prompt-log scanner (experimental stub)."""

from __future__ import annotations

import json
import re
from pathlib import Path

PROMPT_PATTERNS = [
    (r"password\s*[:=]\s*\S+", "credential_leak", 0.9),
    (r"sk-[a-zA-Z0-9]{20,}", "api_key_leak", 0.95),
    (r"\b\d{3}-\d{2}-\d{4}\b", "pii_in_prompt", 0.85),
]


def scan_vectorstore(uri: str, export_path: Path | None = None) -> list[dict]:
    """Scan prompt logs for sensitive content. Experimental."""
    findings: list[dict] = []
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "ai_prompts.json"
    if export_path and export_path.exists():
        prompts = json.loads(export_path.read_text(encoding="utf-8"))
    elif fixture.exists():
        prompts = json.loads(fixture.read_text(encoding="utf-8"))
    else:
        prompts = [{"prompt": "example query with password=secret123", "id": "1"}]
    for p in prompts:
        text = p.get("prompt", "")
        for pattern, ftype, conf in PROMPT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append(
                    {
                        "source": uri,
                        "prompt_excerpt": text[:120],
                        "finding_type": ftype,
                        "confidence": conf,
                        "warning": "experimental — not production-grade",
                    }
                )
    return findings
