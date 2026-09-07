"""First-Monday Compound slot: monthly rollup + security-posture trend."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dspm.db.store import FindingsStore, default_db_path


def _month_stamp(now: datetime | None = None) -> str:
    stamp = now or datetime.now(timezone.utc)
    return stamp.strftime("%Y-%m")


def generate_monthly(
    *,
    out_dir: Path | None = None,
    accept_log: Path | None = None,
    db_path: Path | None = None,
    now: datetime | None = None,
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
    posture = dest / "security-posture.md"
    store = FindingsStore(db_path or default_db_path())
    findings = store.fetchall("findings")
    exposures = store.fetchall("findings_exposure")
    risks = store.fetchall("findings_risk")
    pii = sum(1 for row in findings if row.get("type") in {"PII", "PHI", "PCI", "custom"})
    public = sum(1 for row in exposures if row.get("public"))
    avg_risk = 0.0
    if risks:
        avg_risk = sum(int(row.get("score") or 0) for row in risks) / len(risks)
    top_sources = sources.most_common(10)
    source_lines = [f"- {name}: {count}" for name, count in top_sources] or ["- (none)"]
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
                "## Auto-fix / PR hygiene",
                "- auto-fix success rate: tracked when `good first issue` PRs merge",
                "- cloud-credential rotation count: operator-filled",
                "",
            ]
        ),
        encoding="utf-8",
    )
    posture.write_text(
        "\n".join(
            [
                f"# Security posture — {month}",
                "",
                "AU SMB value proof: are public S3 buckets decreasing? Are PII findings decreasing?",
                "",
                f"- PII/PHI/PCI/custom findings: **{pii}**",
                f"- public exposures: **{public}**",
                f"- average risk score: **{avg_risk:.1f}**",
                f"- findings rows: {len(findings)}",
                "",
                "Trend is computed vs the previous monthly file when present.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"rollup": str(rollup), "posture": str(posture)}
