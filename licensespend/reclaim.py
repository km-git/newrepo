"""Dual-gated reclaim. Draft by default. Never calls vendor revoke APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from licensespend.constants import ALLOW_RECLAIM, apply_enabled


class ReclaimDenied(RuntimeError):
    """Raised when apply is requested without both env and allow-list gates."""


def load_allow_list(path: Path | None = None) -> set[str]:
    target = path or ALLOW_RECLAIM
    if not target.is_file():
        return set()
    return {
        line.strip()
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def reclaim_seats(
    user_ids: list[str],
    *,
    apply: bool = False,
    allow_path: Path | None = None,
) -> dict[str, Any]:
    """Return a draft reclaim pack, or a recorded intent if every gate passes.

    Even when gated apply succeeds this product does not call Graph, Slack, or
    GitHub mutating APIs — it logs operator intent for a human to finish in the
    admin portal.
    """
    unique = [u for u in user_ids if u]
    draft = {
        "action": "draft",
        "user_ids": unique,
        "revoked": False,
        "human_action": "draft email to manager, do not revoke",
    }
    if not apply:
        return draft
    if not apply_enabled():
        raise ReclaimDenied("LICENSESPEND_APPLY is not 1")
    allowed = load_allow_list(allow_path)
    blocked = [uid for uid in unique if uid not in allowed]
    if blocked:
        raise ReclaimDenied(f"user ids not in allow-reclaim.txt: {blocked}")
    return {
        "action": "recorded-intent",
        "user_ids": unique,
        "revoked": False,
        "note": "intent logged; no vendor API revoke was sent",
        "human_action": "complete reclaim in the vendor admin portal",
    }
