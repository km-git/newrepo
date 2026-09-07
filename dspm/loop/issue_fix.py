"""Draft a mechanical fix PR for `good first issue` tickets only."""

from __future__ import annotations

import re
from typing import Any

REQUIRED_HEADINGS = ("expected behavior", "current behavior", "steps to reproduce")


def is_mechanical_issue(title: str, body: str, labels: list[str]) -> dict[str, Any]:
    labels_l = {label.lower() for label in labels}
    if "good first issue" not in labels_l:
        return {"eligible": False, "reason": "missing good first issue label"}
    blob = (body or "").lower()
    if not all(heading in blob for heading in REQUIRED_HEADINGS):
        return {"eligible": False, "reason": "body missing expected/current/steps headings"}
    mechanical = bool(re.search(r"typo|fixture|docs|readme|dependency|bump", (title + " " + blob).lower()))
    if not mechanical:
        return {"eligible": False, "reason": "not a mechanical fix (semantic issues stay with the operator)"}
    return {
        "eligible": True,
        "draft_title": f"fix: auto-attempt for '{title}'",
        "label": "auto-fix-attempted",
        "comment": "willing-to-take: opening a draft PR with a placeholder mechanical fix.",
    }
