"""First-Monday Compound slot: monthly rollup + cost-trend."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from cost.db.store import FindingsStore, default_db_path


def _month_stamp(now: datetime | None = None) -> str:
    stamp = now or datetime.now(UTC)
    return stamp.strftime("%Y-%m")


def generate_monthly(
    *,
    out_dir: Path | None = None,
    accept_log: Path | None = None,
    db_path: Path | None = None,
    now: datetime | None = None,
    gap_audit_path: Path | None = None,
) -> dict[str, str]:
    month = _month_stamp(now)
    dest = out_dir or Path("monthly")
    dest.mkdir(parents=True, exist_ok=True)
    log_path = accept_log or Path("state/accept-reject.jsonl")
    verdicts: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            verdicts[str(row.get("verdict") or "unknown")] += 1
            sources[str(row.get("source") or "unknown")] += 1
    rollup = dest / f"{month}.md"
    trend = dest / "cost-trend.md"
    store = FindingsStore(db_path or default_db_path())
    costs = store.fetchall("findings_costs")
    rightsizing = store.fetchall("findings_rightsizing")
    untagged = store.fetchall("findings_untagged")
    total_spend = sum(float(r.get("amount") or 0) for r in costs)
    savings = sum(float(r.get("monthly_savings_estimate") or 0) for r in rightsizing)
    top_sources = sources.most_common(10)
    source_lines = [f"- {name}: {count}" for name, count in top_sources] or ["- (none)"]
    gap_lines = ["- (run `cost loop gap-audit` / `cost loop improve`)"]
    gap_path = gap_audit_path or Path("state/gap_audit.json")
    if gap_path.exists():
        try:
            gap_report = json.loads(gap_path.read_text(encoding="utf-8"))
            nxt = gap_report.get("next_integrations") or []
            if nxt:
                gap_lines = [f"- {row.get('name')} → `{row.get('module')}` [{row.get('impact')}]" for row in nxt[:8]]
        except json.JSONDecodeError:
            # Invalid gap_audit.json: keep the default next-integration placeholders.
            pass
    rollup.write_text(
        "\n".join(
            [
                f"# Monthly rollup — {month}",
                "",
                "## Discover accept/reject",
                f"- discover: {verdicts.get('discover', 0)}",
                f"- watch: {verdicts.get('watch', 0)}",
                f"- skip: {verdicts.get('skip', 0)}",
                "",
                "## Top sources",
                *source_lines,
                "",
                "## Next OSS integrations (gap audit)",
                *gap_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    trend.write_text(
        "\n".join(
            [
                f"# Cost trend — {month}",
                "",
                "Is monthly spend decreasing? Are rightsizing recommendations being reviewed?",
                "Is the untagged-resource count dropping?",
                "",
                f"- total observed spend (fixture/rollup rows): **{total_spend:.2f}**",
                f"- rightsizing opportunities: **{len(rightsizing)}** (~{savings:.2f}/mo potential)",
                f"- untagged resources: **{len(untagged)}**",
                "",
                "Cost data has a 24-48h lag; compare month-over-month using stored rollups.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"rollup": str(rollup), "cost_trend": str(trend)}
