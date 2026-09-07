"""Mechanical good-first-issue gate. Semantic issues stay with the operator."""

from __future__ import annotations

import re
from typing import Any

HEADINGS = ("expected behavior", "current behavior", "steps to reproduce")


def is_mechanical_issue(title: str, body: str, labels: list[str]) -> dict[str, Any]:
    blob = body.lower()
    labeled = [label.lower() for label in labels]
    if "good first issue" not in labeled and "good first issue" not in blob:
        return {"eligible": False, "reason": "missing good first issue label"}
    if not all(h in blob for h in HEADINGS):
        return {"eligible": False, "reason": "body missing expected/current/steps headings"}
    if re.search(r"disclaimer|sspm/loop|live.connector|oauth scope", (title + " " + blob), re.I):
        return {"eligible": False, "reason": "touches disclaimer, loop, or live-connector scopes"}
    mechanical = bool(re.search(r"typo|fixture|docs|readme|dependency|bump", (title + " " + blob).lower()))
    if not mechanical:
        return {"eligible": False, "reason": "not a mechanical fix (semantic issues stay with the operator)"}
    return {
        "eligible": True,
        "draft_title": f"fix: auto-attempt for '{title}'",
        "label": "auto-fix-attempted",
        "comment": "willing-to-take: opening a draft PR with a placeholder mechanical fix.",
    }
