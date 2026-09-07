"""Bot-only auto-approval policy. Human PRs and remediation policies never auto-merge."""

from __future__ import annotations

from dspm.remediation.service import should_block_auto_merge

BOT_ACTORS = frozenset({"dependabot[bot]", "github-actions[bot]"})
AUTO_MARK = "[auto-approved]"


def should_auto_approve(
    *,
    actor: str,
    body: str = "",
    changed_files: list[str] | None = None,
) -> dict[str, object]:
    files = changed_files or []
    if should_block_auto_merge(files):
        return {"approve": False, "reason": "remediation policies require manual review"}
    if actor in BOT_ACTORS:
        return {"approve": True, "reason": f"bot actor {actor}"}
    if AUTO_MARK in (body or ""):
        return {"approve": True, "reason": "body contains [auto-approved]"}
    return {"approve": False, "reason": "human or unknown actor — manual review required"}
