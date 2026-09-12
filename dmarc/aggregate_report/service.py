"""DuckDB/SQLite roll-up + standalone HTML (plotly when installed)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dmarc.aggregate_report.models import SourceSummary
from dmarc.forbidden import sanitize_report_text
from dmarc.paths import DISCLAIMER_PATH, output_dir
from dmarc.store import fetch_all


def _since_cutoff(since: str) -> str | None:
    raw = since.strip().lower()
    if raw.endswith("d") and raw[:-1].isdigit():
        days = int(raw[:-1])
        stamp = datetime.now(UTC) - timedelta(days=days)
        return stamp.replace(microsecond=0).isoformat()
    return None


def summarize(domain: str | None = None, since: str = "30d", root: Path | None = None) -> dict[str, Any]:
    cutoff = _since_cutoff(since)
    rows = fetch_all("findings_dmarc", domain=domain, root=root, since=cutoff)
    by_org: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "pass": 0, "fail": 0})
    by_ip: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "pass": 0, "fail": 0})
    dispositions: dict[str, int] = defaultdict(int)
    for row in rows:
        count = int(row.get("count") or 0)
        aligned = str(row.get("dkim_result")) == "pass" or str(row.get("spf_result")) == "pass"
        org = str(row.get("source_org") or "unknown")
        ip = str(row.get("source_ip") or "unknown")
        by_org[org]["count"] += count
        by_ip[ip]["count"] += count
        if aligned:
            by_org[org]["pass"] += count
            by_ip[ip]["pass"] += count
        else:
            by_org[org]["fail"] += count
            by_ip[ip]["fail"] += count
        dispositions[str(row.get("disposition") or "none")] += count
    sources = [
        SourceSummary(
            source_org=org,
            source_ip="",
            count=vals["count"],
            pass_count=vals["pass"],
            fail_count=vals["fail"],
            pass_rate=(vals["pass"] / vals["count"]) if vals["count"] else 0.0,
        ).model_dump()
        for org, vals in sorted(by_org.items(), key=lambda item: item[1]["count"], reverse=True)
    ]
    ips = [
        SourceSummary(
            source_org="",
            source_ip=ip,
            count=vals["count"],
            pass_count=vals["pass"],
            fail_count=vals["fail"],
            pass_rate=(vals["pass"] / vals["count"]) if vals["count"] else 0.0,
        ).model_dump()
        for ip, vals in sorted(by_ip.items(), key=lambda item: item[1]["count"], reverse=True)[:20]
    ]
    total = sum(int(r.get("count") or 0) for r in rows)
    passed = sum(s["pass_count"] for s in sources)
    return {
        "domain": domain,
        "since": since,
        "message_count": total,
        "pass_count": passed,
        "pass_rate": (passed / total) if total else 0.0,
        "dispositions": dict(dispositions),
        "by_org": sources,
        "by_ip": ips,
        "row_count": len(rows),
        "reject_ready": bool(total and (passed / total) >= 0.99),
    }


def _plotly_html(summary: dict[str, Any]) -> str | None:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        return None
    orgs = summary["by_org"][:12]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Pass / fail by source", "Top sending IPs"))
    fig.add_trace(
        go.Bar(name="pass", x=[o["source_org"] for o in orgs], y=[o["pass_count"] for o in orgs]),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(name="fail", x=[o["source_org"] for o in orgs], y=[o["fail_count"] for o in orgs]),
        row=1,
        col=1,
    )
    ips = summary["by_ip"][:12]
    fig.add_trace(
        go.Bar(x=[i["source_ip"] for i in ips], y=[i["count"] for i in ips], name="messages"),
        row=1,
        col=2,
    )
    fig.update_layout(title="Email Deliverability & Brand-Protection Review — aggregate", barmode="stack")
    return fig.to_html(include_plotlyjs="cdn", full_html=True)


def _svg_bars(summary: dict[str, Any]) -> str:
    orgs = summary["by_org"][:8] or [{"source_org": "(none)", "pass_count": 0, "fail_count": 0, "count": 1}]
    max_count = max(o["count"] for o in orgs) or 1
    bars = []
    y = 20
    for org in orgs:
        pw = int(280 * org["pass_count"] / max_count)
        fw = int(280 * org["fail_count"] / max_count)
        bars.append(
            f'<text x="8" y="{y + 12}" fill="#e6edf3" font-size="11">{org["source_org"]}</text>'
            f'<rect x="140" y="{y}" width="{pw}" height="14" fill="#3fb950"/>'
            f'<rect x="{140 + pw}" y="{y}" width="{fw}" height="14" fill="#f85149"/>'
        )
        y += 22
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="520" height="{y + 10}">{"".join(bars)}</svg>'


def write_html(summary: dict[str, Any], dest: Path | None = None, root: Path | None = None) -> Path:
    month = datetime.now(UTC).strftime("%Y-%m")
    dest = dest or (output_dir(root) / "reports" / f"aggregate_{month}.html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    disclaimer = DISCLAIMER_PATH.read_text(encoding="utf-8") if DISCLAIMER_PATH.exists() else ""
    body = _plotly_html(summary)
    if not body:
        body = (
            "<html><head><meta charset='utf-8'><title>Deliverability aggregate</title></head>"
            "<body style='background:#0d1117;color:#e6edf3;font-family:sans-serif'>"
            "<h1>Email Deliverability &amp; Brand-Protection Review</h1>"
            f"{_svg_bars(summary)}<pre>{disclaimer}</pre></body></html>"
        )
    else:
        body = body.replace("</body>", f"<pre>{disclaimer}</pre></body>")
    dest.write_text(sanitize_report_text(body), encoding="utf-8")
    return dest


def run_report(domain: str | None = None, since: str = "30d", root: Path | None = None) -> dict[str, Any]:
    summary = summarize(domain=domain, since=since, root=root)
    html = write_html(summary, root=root)
    summary["html"] = str(html)
    return summary
