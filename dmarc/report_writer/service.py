"""Jinja2 (or stdlib) Markdown/JSON review with the AU liability disclaimer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dmarc.aggregate_report.service import summarize
from dmarc.audit.service import run_inventory
from dmarc.dkim_check.service import check_domain as check_dkim
from dmarc.dns_check.service import check_domain as check_dns
from dmarc.forbidden import contains_forbidden, sanitize_report_text
from dmarc.forensic_report.service import list_forensic
from dmarc.inbox_placement.service import run_test
from dmarc.paths import DISCLAIMER_PATH, REPORT_TEMPLATE, output_dir
from dmarc.spf_parser.service import parse_domain
from dmarc.store import dump_json, fetch_all, utcnow

TITLE = "Email Deliverability & Brand-Protection Review"

FALLBACK_TEMPLATE = """# {{ title }}

Domain: **{{ domain }}**
Generated: {{ generated_at }}

## DNS check summary

{{ dns_md }}

## SPF / DKIM / DMARC findings

### SPF
{{ spf_md }}

### DKIM
{{ dkim_md }}

### DMARC aggregate
{{ dmarc_md }}

Do not move to `p=reject` until the aggregate pass rate is at least 99% for 30 days. Premature reject drops legitimate mail.

## Aggregate chart

See `{{ aggregate_note }}`.

## Inbox placement trend

{{ inbox_md }}

Placement is heuristic and can change daily. Track weekly.

## Forensic (RUF)

{{ forensic_md }}

---

{{ disclaimer }}
"""


def _disclaimer() -> str:
    if DISCLAIMER_PATH.exists():
        return DISCLAIMER_PATH.read_text(encoding="utf-8").strip()
    return (
        "This Email Deliverability & Brand-Protection Review is observational only. "
        "It is not legal advice, not an audit opinion, and not a warranty of inbox placement."
    )


def _render(template: str, ctx: dict[str, Any]) -> str:
    try:
        from jinja2 import BaseLoader, Environment

        env = Environment(loader=BaseLoader(), autoescape=True)
        return env.from_string(template).render(**ctx)
    except ImportError:
        out = template
        for key, value in ctx.items():
            out = out.replace("{{ " + key + " }}", str(value))
        return out


def _md_table(rows: list[dict[str, Any]], keys: list[str]) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(keys) + " |"
    sep = "| " + " | ".join("---" for _ in keys) + " |"
    lines = [header, sep]
    for row in rows[:40]:
        lines.append("| " + " | ".join(str(row.get(k, ""))[:80] for k in keys) + " |")
    return "\n".join(lines)


def generate(
    domain: str,
    since: str = "30d",
    output: Path | None = None,
    root: Path | None = None,
    run_live: bool = True,
    resolver: Any = None,
) -> dict[str, Any]:
    root_path = Path(root) if root else output_dir()
    if run_live:
        dns_rows = check_dns(domain, resolver=resolver, root=root_path)
        spf = parse_domain(domain, resolver=resolver, root=root_path)
        dkim_rows = check_dkim(domain, resolver=resolver, root=root_path)
    else:
        dns_rows = fetch_all("findings_dns", domain=domain, root=root_path)
        spf_rows = fetch_all("findings_spf", domain=domain, root=root_path)
        spf = spf_rows[0] if spf_rows else {}
        dkim_rows = fetch_all("findings_dkim", domain=domain, root=root_path)
    aggregate = summarize(domain=domain, since=since, root=root_path)
    forensic = list_forensic(since=since, domain=domain, root=root_path)
    inbox = fetch_all("findings_inbox", root=root_path)
    if not inbox:
        inbox = run_test(f"noreply@{domain}", [], dry_run=True, root=root_path)
    inventory = run_inventory(root_path)

    reject_note = (
        "Observed pass rate is below 99%; keep `p=none` or `p=quarantine` until the trend holds for 30 days."
        if not aggregate.get("reject_ready")
        else "Observed pass rate is ≥ 99% in this window — still an observation, not a policy instruction."
    )
    template = REPORT_TEMPLATE.read_text(encoding="utf-8") if REPORT_TEMPLATE.exists() else FALLBACK_TEMPLATE
    ctx = {
        "title": TITLE,
        "domain": domain,
        "generated_at": utcnow(),
        "dns_md": _md_table(dns_rows, ["record_type", "value", "ttl"]),
        "spf_md": json.dumps(spf, indent=2, default=str) if isinstance(spf, dict) else str(spf),
        "dkim_md": _md_table(dkim_rows, ["selector", "public_key_length", "warnings"]),
        "dmarc_md": (
            f"Messages: {aggregate.get('message_count')} · pass rate: "
            f"{aggregate.get('pass_rate', 0):.1%}\n\n{reject_note}\n\n"
            + _md_table(aggregate.get("by_org") or [], ["source_org", "count", "pass_count", "fail_count", "pass_rate"])
        ),
        "aggregate_note": "output/dmarc/reports/aggregate_YYYY-MM.html (Plotly or SVG)",
        "inbox_md": _md_table(inbox, ["provider", "seed_account", "placement", "sent_at"]),
        "forensic_md": _md_table(forensic, ["source_ip", "from_address", "subject", "dkim_result"])
        if forensic
        else "_No RUF reports in this window (common; many senders omit forensic copies)._",
        "disclaimer": _disclaimer(),
        "inventory_count": len((inventory or {}).get("tools") or []),
    }
    markdown = sanitize_report_text(_render(template, ctx))
    if contains_forbidden(markdown):
        markdown = sanitize_report_text(markdown)
    dest = Path(output) if output else root_path / "report.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(markdown if markdown.endswith("\n") else markdown + "\n", encoding="utf-8")
    json_payload = {
        "title": TITLE,
        "domain": domain,
        "generated_at": ctx["generated_at"],
        "dns": dns_rows,
        "spf": spf,
        "dkim": dkim_rows,
        "aggregate": aggregate,
        "inbox": inbox,
        "forensic": forensic,
        "disclaimer": _disclaimer(),
    }
    json_path = dump_json("report.json", json_payload, root_path)
    return {
        "title": TITLE,
        "domain": domain,
        "markdown_path": str(dest),
        "json_path": str(json_path),
        "sections": ["dns", "spf", "dkim", "dmarc", "aggregate", "inbox", "disclaimer"],
    }
