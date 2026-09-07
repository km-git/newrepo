"""Markdown + JSON report generation with liability disclaimer."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jinja2 import Template

from cost.constants import FORBIDDEN_REPORT_WORDS
from cost.db.store import FindingsStore

DISCLAIMER_PATH = Path(__file__).resolve().parents[2] / "disclaimers" / "disclaimer_au.txt"
TEMPLATE = Template(
    """# Cloud Cost & Configuration Review

**Provider:** {{ provider }}
**Period:** {{ since }}
**Generated:** {{ generated_at }}

## Cost summary

Total cost rows: {{ cost_count }}
Top drivers:
{% for row in top_costs %}
- {{ row.service }} ({{ row.region }}): {{ row.amount }}
{% endfor %}

## Rightsizing opportunities

Count: {{ rightsizing_count }}
Review with the engineering team before applying.

## Untagged inventory

Count: {{ untagged_count }}

## Configuration drift

Count: {{ drift_count }}

## Framework references

Mapped controls: {{ compliance_count }}
This section provides **framework reference** mappings only — not attestation.

---

{{ disclaimer }}
""",
    autoescape=True,
)


def _scrub(text: str) -> str:
    out = text
    for word in FORBIDDEN_REPORT_WORDS:
        out = re.sub(rf"\b{word}\b", "configuration reference", out, flags=re.I)
    return out


def generate(
    *,
    provider: str = "aws",
    since: str = "30d",
    output: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    db = store or FindingsStore()
    costs = db.fetchall("findings_costs", "provider = ?", (provider,))
    rightsizing = db.fetchall("findings_rightsizing", "provider = ?", (provider,))
    untagged = db.fetchall("findings_untagged")
    drift = db.fetchall("findings_drift", "provider = ?", (provider,))
    compliance = db.fetchall("findings_compliance")
    top_costs = sorted(costs, key=lambda r: float(r.get("amount", 0)), reverse=True)[:5]
    disclaimer = (
        DISCLAIMER_PATH.read_text(encoding="utf-8")
        if DISCLAIMER_PATH.exists()
        else ("This report is a read-only cost and configuration observation.")
    )
    md = TEMPLATE.render(
        provider=provider,
        since=since,
        generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        cost_count=len(costs),
        top_costs=top_costs,
        rightsizing_count=len(rightsizing),
        untagged_count=len(untagged),
        drift_count=len(drift),
        compliance_count=len(compliance),
        disclaimer=disclaimer.strip(),
    )
    md = _scrub(md)
    out_md = output or Path("output/cost/report.md")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    payload = {
        "title": "Cloud Cost & Configuration Review",
        "provider": provider,
        "since": since,
        "counts": {
            "costs": len(costs),
            "rightsizing": len(rightsizing),
            "untagged": len(untagged),
            "drift": len(drift),
            "framework_references": len(compliance),
        },
        "markdown_path": str(out_md),
    }
    out_json = out_md.with_suffix(".json")
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload["json_path"] = str(out_json)
    return payload
