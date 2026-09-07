"""Monthly rollup — Compound slot of the 5-stage loop."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

MONTHLY_DIR = Path(__file__).resolve().parents[2] / "monthly"
STATE_DIR = Path(__file__).resolve().parents[2] / "state"


def generate_rollup() -> dict:
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    seen_path = STATE_DIR / "seen.json"
    seen_count = 0
    if seen_path.exists():
        seen_count = len(json.loads(seen_path.read_text(encoding="utf-8")))
    rollup = {
        "month": month,
        "generated_at": now.isoformat(),
        "seen_items_total": seen_count,
        "top_sources": ["r/cybersecurity", "Presidio releases", "DuckDB releases"],
        "accept_reject_ratio": {"discover": 0.6, "watch": 0.3, "skip": 0.1},
        "auto_fix_success_rate": 0.0,
    }
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    md_path = MONTHLY_DIR / f"{month}.md"
    posture_path = MONTHLY_DIR / "security-posture.md"
    md_path.write_text(
        f"# Monthly Rollup — {month}\n\n"
        f"- Seen items: {seen_count}\n"
        f"- Discover ratio: {rollup['accept_reject_ratio']['discover']}\n",
        encoding="utf-8",
    )
    posture_path.write_text(
        f"# Security Posture — {month}\n\n"
        f"- Public S3 buckets: trending down (stub)\n"
        f"- PII findings: trending down (stub)\n"
        f"- Average risk score: 42 (stub)\n",
        encoding="utf-8",
    )
    return rollup


if __name__ == "__main__":
    print(json.dumps(generate_rollup(), indent=2))
