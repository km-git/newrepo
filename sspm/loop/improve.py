"""5-stage improve cycle: Discover → Evaluate → Integrate → Validate → Compound."""

from __future__ import annotations

from sspm.loop.monthly import generate_monthly
from sspm.loop.watch import watch


def improve(*, fetch: bool = False) -> dict:
    watch_result = watch(fetch=fetch)
    monthly = generate_monthly()
    return {
        "stage": "compound",
        "watch": watch_result,
        "monthly": monthly,
        "discoveries_count": len(watch_result.get("discoveries", [])),
    }
