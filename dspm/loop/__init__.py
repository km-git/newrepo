"""5-stage Discover→Evaluate→Integrate→Validate→Compound watcher."""

from dspm.loop import auto_approve, issue_fix, monthly, watch

__all__ = ["auto_approve", "issue_fix", "monthly", "watch"]
