"""Draft a good-first-issue fix PR body (no human-PR auto-approve)."""

from __future__ import annotations

from pathlib import Path


def draft_issue_fix(title: str, body: str, number: int, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = (
        f"# Draft fix for #{number}: {title}\n\n"
        f"{body.strip()}\n\n"
        "This draft is produced by the dmarc issue auto-fix workflow. "
        "A human operator must review before merge. Bot auto-approve does not apply.\n"
    )
    dest.write_text(text, encoding="utf-8")
    return dest
