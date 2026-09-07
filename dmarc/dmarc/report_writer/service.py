"""Markdown + JSON report writer with AU liability disclaimer."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

from dmarc.config import DISALLOWED_WORDS, DISCLAIMER_PATH, REPORTS_DIR
from dmarc.db import fetch_all, init_db


def _sanitize(text: str) -> str:
    out = text
    for word in DISALLOWED_WORDS:
        out = re.sub(rf"\b{word}\b", "deliverability observation", out, flags=re.IGNORECASE)
    return out


def _load_disclaimer() -> str:
    if DISCLAIMER_PATH.is_file():
        return DISCLAIMER_PATH.read_text(encoding="utf-8")
    return "Liability disclaimer unavailable."


REPORT_TEMPLATE = Template(
    """# Email Deliverability & Brand-Protection Review

**Domain:** {{ domain }}
**Generated:** {{ generated_at }}
**Period:** last {{ since }}

> This is a read-only deliverability + brand-protection report — not an email security assessment.

## DNS check summary

Records observed: {{ dns_count }}

{% for row in dns[:15] %}
- `{{ row.record_type }}` → {{ row.value[:120] }}{% if row.value|length > 120 %}…{% endif %}
{% endfor %}

## SPF findings

{% if spf %}
- Record: `{{ spf.record }}`
- DNS lookups: {{ spf.dns_lookup_count }} (limit 10)
- `all` qualifier: `{{ spf.all_qualifier }}`
{% for w in spf.warnings %}- ⚠ {{ w }}
{% endfor %}
{% else %}
- No SPF row stored yet.
{% endif %}

## DKIM findings

{% for d in dkim[:8] %}
- Selector `{{ d.selector }}`: key {{ d.public_key_length or 'n/a' }} bits
  {%- for w in d.warnings %} — {{ w }}{% endfor %}
{% endfor %}

## DMARC aggregate summary

Rows: {{ dmarc_count }} · Pass-like rows: {{ dmarc_pass }}

{% if dmarc_top %}
| Source org | Count | DKIM | SPF |
|---|---:|---|---|
{% for r in dmarc_top %}
| {{ r.source_org }} | {{ r.count }} | {{ r.dkim_result }} | {{ r.spf_result }} |
{% endfor %}
{% endif %}

## Inbox placement trend

{% for i in inbox %}
- {{ i.provider }} / {{ i.seed_account }}: **{{ i.placement }}**
{% endfor %}

## Policy guidance

Do **not** move to `p=reject` until aggregate reports show ≥99% pass rate for at least 30 days.

---

## Liability disclaimer

{{ disclaimer }}
"""
)


def generate_report(domain: str, since: str = "30d", output: Path | None = None) -> tuple[Path, Path]:
    init_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc)
    md_path = output or REPORTS_DIR / f"report_{domain.replace('.', '_')}.md"
    json_path = md_path.with_suffix(".json")

    dns = fetch_all("findings_dns")
    spf_rows = fetch_all("findings_spf")
    dkim = fetch_all("findings_dkim")
    dmarc = fetch_all("findings_dmarc")
    inbox = fetch_all("findings_inbox")

    spf = spf_rows[0] if spf_rows else None
    dmarc_pass = sum(1 for r in dmarc if r.get("dkim_result") == "pass" and r.get("spf_result") == "pass")
    dmarc_top = dmarc[:10]

    disclaimer = _sanitize(_load_disclaimer())
    body = REPORT_TEMPLATE.render(
        domain=domain,
        generated_at=stamp.isoformat(),
        since=since,
        dns_count=len(dns),
        dns=dns,
        spf=spf,
        dkim=dkim,
        dmarc_count=len(dmarc),
        dmarc_pass=dmarc_pass,
        dmarc_top=dmarc_top,
        inbox=inbox,
        disclaimer=disclaimer,
    )
    body = _sanitize(body)
    md_path.write_text(body, encoding="utf-8")

    payload = {
        "title": "Email Deliverability & Brand-Protection Review",
        "domain": domain,
        "since": since,
        "generated_at": stamp.isoformat(),
        "dns_count": len(dns),
        "spf": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in (spf or {}).items()},
        "dkim_count": len(dkim),
        "dmarc_count": len(dmarc),
        "inbox_count": len(inbox),
        "disclaimer": disclaimer,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return md_path, json_path
