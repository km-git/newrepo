"""Monthly deliverability-trend rollup (first Monday 09:00 AEST payload)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from dmarc.aggregate_report.service import summarize
from dmarc.forbidden import sanitize_report_text
from dmarc.paths import MONTHLY_DIR
from dmarc.store import fetch_all


def write_monthly(root: Path | None = None, monthly_dir: Path | None = None) -> dict[str, str]:
    dest_dir = Path(monthly_dir) if monthly_dir else MONTHLY_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    month = datetime.now(UTC).strftime("%Y-%m")
    summary = summarize(since="30d", root=root)
    inbox = fetch_all("findings_inbox", root=root)
    forensic = fetch_all("findings_forensic", root=root)
    spoofish = sum(
        int(r.get("count") or 0)
        for r in fetch_all("findings_dmarc", root=root)
        if r.get("disposition") in {"quarantine", "reject"} or r.get("spf_result") == "fail"
    )
    trend = sanitize_report_text(
        "\n".join(
            [
                f"# Deliverability trend — {month}",
                "",
                f"- DMARC aligned pass rate: {summary.get('pass_rate', 0):.1%} "
                f"over {summary.get('message_count')} messages",
                f"- Inbox placement probes this window: {len(inbox)}",
                f"- Forensic (RUF) rows: {len(forensic)} (empty is common)",
                f"- Fail / quarantine volume (spoofing attempts proxy): {spoofish}",
                "- Direction: treat rising pass rate and falling fail volume as improvement.",
                "- This is an observation, not a warranty.",
                "",
            ]
        )
    )
    monthly = sanitize_report_text(
        "\n".join(
            [
                f"# Monthly rollup — {month}",
                "",
                "Discover → Evaluate → Integrate → Validate → Compound.",
                "",
                f"Pass rate: {summary.get('pass_rate', 0):.1%}",
                f"Sources: {len(summary.get('by_org') or [])}",
                "",
            ]
        )
    )
    trend_path = dest_dir / "deliverability-trend.md"
    month_path = dest_dir / f"{month}.md"
    trend_path.write_text(trend + "\n", encoding="utf-8")
    month_path.write_text(monthly + "\n", encoding="utf-8")
    return {"trend": str(trend_path), "monthly": str(month_path)}
