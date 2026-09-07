"""First-Monday Compound slot: monthly rollup (not an attestation)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def generate_monthly(*, out_dir: Path | None = None, now: datetime | None = None) -> dict[str, str]:
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m")
    dest = out_dir or Path("monthly")
    dest.mkdir(parents=True, exist_ok=True)
    queue = Path("state/discover_queue.json")
    verdicts: Counter[str] = Counter()
    if queue.exists():
        for item in json.loads(queue.read_text(encoding="utf-8")):
            verdicts[str((item.get("classification") or {}).get("verdict") or "unknown")] += 1
    rollup = dest / f"{stamp}.md"
    body = f"""# SSPM monthly rollup — {stamp}

Discover verdicts this cycle: {dict(verdicts)}

## Posture observation trend

Track: MFA coverage up? guest links down? OAuth grants down?
This file is a Compound-slot note, not an attestation.

## Next Monday 09:00 AEST

1. Review `state/discover_queue.json`
2. Auto-approved bot PRs only
3. Operator-review `sspm/disclaimers/` and `sspm/loop/`
"""
    rollup.write_text(body, encoding="utf-8")
    return {"month": stamp, "path": str(rollup)}
