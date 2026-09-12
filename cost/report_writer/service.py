"""cost/report_writer — Cloud Cost & Configuration Review markdown + JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cost.cost_explorer.service import LAG_NOTE
from cost.db.store import fetch_all, init_schema
from cost.fixtures import tenant_id, tenant_name
from cost.language import assert_report_language, scrub_report_text
from cost.paths import DISCLAIMER_PATH, REPORT_JSON, REPORT_MD, ensure_output
from cost.rightsizing.service import REVIEW
from cost.untagged.service import ORG_NOTE

TITLE = "Cloud Cost & Configuration Review"


def _disclaimer() -> str:
    if DISCLAIMER_PATH.is_file():
        return DISCLAIMER_PATH.read_text(encoding="utf-8").strip()
    return (
        "This document is a read-only Cloud Cost & Configuration Review prepared from "
        "customer-authorised control-plane APIs and/or sandbox fixtures. It is not legal, "
        "financial, or professional advice. Figures may lag 24-48 hours. Rightsizing rows "
        "are heuristic observations. Review with the engineering team before applying any "
        "change. No warranty is offered. Operator liability is limited to the fee paid for "
        "this review (often $0)."
    )


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_None in this review window._"
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def run(
    *,
    sandbox: bool = True,
    provider: str = "all",
    since: str = "30d",
    output: str = "",
    **_kwargs: Any,
) -> dict[str, Any]:
    ensure_output()
    conn = init_schema()
    tid = tenant_id()
    costs = fetch_all(conn, "findings_costs", tid)
    resources = fetch_all(conn, "findings_resources", tid)
    rightsizing = fetch_all(conn, "findings_rightsizing", tid)
    untagged = fetch_all(conn, "findings_untagged", tid)
    drift = fetch_all(conn, "findings_drift", tid)
    framework = fetch_all(conn, "findings_compliance", tid)
    if provider not in {"", "all"}:
        costs = [r for r in costs if r.get("provider") == provider]
        resources = [r for r in resources if r.get("provider") == provider]
        rightsizing = [r for r in rightsizing if r.get("provider") == provider]
        untagged = [r for r in untagged if r.get("provider") == provider]
        drift = [r for r in drift if r.get("provider") == provider]

    total = round(sum(float(r.get("amount") or 0) for r in costs), 2)
    savings = round(sum(float(r.get("monthly_savings_estimate") or 0) for r in rightsizing), 2)
    untagged_spend = round(sum(float(r.get("monthly_cost") or 0) for r in untagged), 2)
    generated = datetime.now(UTC).replace(microsecond=0).isoformat()

    drivers = sorted(costs, key=lambda r: float(r.get("amount") or 0), reverse=True)[:8]
    driver_table = _md_table(
        ["Provider", "Service", "Period", "Amount (USD)"],
        [
            [str(r.get("provider")), str(r.get("service")), str(r.get("period")), f"{float(r.get('amount') or 0):.2f}"]
            for r in drivers
        ],
    )
    rs_table = _md_table(
        ["Resource", "Current", "Suggested", "Est. monthly savings", "Risk"],
        [
            [
                str(r.get("resource_id")),
                str(r.get("current_type")),
                str(r.get("recommended_type")),
                f"{float(r.get('monthly_savings_estimate') or 0):.2f}",
                str(r.get("risk_level")),
            ]
            for r in rightsizing
        ],
    )
    un_table = _md_table(
        ["Resource", "Type", "Missing tags", "Monthly cost"],
        [
            [
                str(r.get("resource_id")),
                str(r.get("resource_type")),
                str(r.get("missing_tags")),
                f"{float(r.get('monthly_cost') or 0):.2f}",
            ]
            for r in untagged
        ],
    )
    drift_table = _md_table(
        ["Resource", "Field", "Baseline", "Current"],
        [
            [str(r.get("resource_id")), str(r.get("field")), str(r.get("baseline")), str(r.get("current_value"))]
            for r in drift
        ],
    )
    fw_table = _md_table(
        ["Control", "Name", "Mapping status"],
        [[str(r.get("control_id")), str(r.get("control_name")), str(r.get("status"))] for r in framework],
    )

    body = f"""# {TITLE}

**Tenant:** {tenant_name()}  
**Provider scope:** {provider}  
**Window:** {since}  
**Generated (UTC):** {generated}  
**Mode:** {"sandbox fixtures" if sandbox else "customer control-plane APIs"}

This is a **Cloud Cost & Configuration Review**. It is not a security assessment.

## 1. Cost summary

Estimated spend in the reviewed window: **USD {total:.2f}**.  
Heuristic rightsizing savings if reviewed and applied: **USD {savings:.2f} / month**.  
Spend on resources missing required tags: **USD {untagged_spend:.2f} / month**.

{LAG_NOTE}

## 2. Top cost drivers

{driver_table}

## 3. Rightsizing opportunities

{REVIEW}

{rs_table}

## 4. Untagged inventory

{ORG_NOTE}

{un_table}

## 5. Configuration drift (cost-relevant)

Instance type, storage class, and reserved-instance / savings-plan expiry observations.

{drift_table}

## 6. Framework references

Mapping only — this is not an audit opinion.

{fw_table}

## 7. Resource inventory count

{len(resources)} resources were inventoried for this review.

## 8. Liability disclaimer

{_disclaimer()}
"""
    text = scrub_report_text(body)
    assert_report_language(text)
    md_path = Path(output) if output else REPORT_MD
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(text, encoding="utf-8")
    payload = {
        "title": TITLE,
        "tenant": tenant_name(),
        "provider": provider,
        "since": since,
        "generated_at": generated,
        "sandbox": sandbox,
        "totals": {"spend": total, "rightsizing_savings": savings, "untagged_spend": untagged_spend},
        "lag_note": LAG_NOTE,
        "review_with_engineering": REVIEW,
        "disclaimer": _disclaimer(),
        "markdown_path": str(md_path),
    }
    json_path = REPORT_JSON
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown"] = text
    payload["disclaimer"] = _disclaimer()
    return payload
