"""Monthly rollup for SSPM improvement loop."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MONTHLY = ROOT / "monthly"


def generate_monthly() -> dict[str, str]:
    MONTHLY.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m")
    path = MONTHLY / f"{stamp}.md"
    body = f"""# SSPM Monthly Rollup — {stamp}

## Summary
- Modules: 12 + loop + web UI
- Report type: Configuration & Inventory Report (read-only)
- Primary scanner: Mondoo cnspec (subprocess when available)

## Discoveries
See `discoveries/sspm/` for weekly forum-watcher output.

## Next integrations
- Live cnspec policy packs for CIS-M365 and CIS-GWS
- Partner MSP registry population

---
*Auto-generated monthly rollup. Not a security assessment.*
"""
    path.write_text(body, encoding="utf-8")
    return {"path": str(path), "month": stamp}
