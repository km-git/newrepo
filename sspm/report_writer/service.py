"""Configuration & Inventory Report writer (Markdown + JSON + HTML)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sspm import FORBIDDEN_REPORT_WORDS, __version__
from sspm.compliance_map.service import map_tenant
from sspm.config_drift.service import diff_tenant
from sspm.disclaimers.service import append_to, show
from sspm.discovery import load_fixture
from sspm.oauth_grants.service import list_grants
from sspm.redact import scrub_text
from sspm.report_writer.models import ReportFiles

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
WORD_RE = {word: re.compile(rf"\b{re.escape(word)}\b", re.I) for word in FORBIDDEN_REPORT_WORDS}


def _render_markdown(ctx: dict[str, Any]) -> str:
    template_path = TEMPLATE_DIR / "report.md.j2"
    if template_path.exists():
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape

            env = Environment(
                loader=FileSystemLoader(str(TEMPLATE_DIR)),
                autoescape=select_autoescape(enabled_extensions=()),
            )
            return env.get_template("report.md.j2").render(**ctx)
        except ImportError:
            pass
    return _fallback_markdown(ctx)


def _fallback_markdown(ctx: dict[str, Any]) -> str:
    settings = "\n".join(f"- `{s['name']}` = `{s['value']}` ({s.get('source', '')})" for s in ctx["settings"])
    drift = (
        "\n".join(f"- `{d['setting_name']}`: {d.get('old_value')} → {d.get('new_value')}" for d in ctx["drift"])
        or "- none observed against the shipped baseline"
    )
    oauth = (
        "\n".join(
            f"- {g['app_name']} ({g['publisher']}) scopes `{g['scopes']}` risk={g['risk_level']}" for g in ctx["oauth"]
        )
        or "- none"
    )
    refs = "\n".join(
        f"- {r['framework']} {r['control_id']}: {r['title']} — {r['reference_status']}" for r in ctx["control_refs"]
    )
    return f"""# Configuration & Inventory Report

**Customer:** {ctx["display_name"]}
**Tenant type:** {ctx["tenant_type"]}
**Generated:** {ctx["generated_at"]}
**Tool version:** {ctx["version"]}
**Scanner:** {ctx["scanner"]}

This is a Configuration & Inventory Report. It is not a security assessment and not an audit.

## Honest gap

{ctx["honest_gap"]}

## Tenant inventory

{settings}

## Drift versus shipped baseline

{drift}

## OAuth grants (scopes only)

{oauth}

## Control references

The table below is a mapping aid. A "matches-reference" label is not a control status.

{refs}

## Method

Read-only APIs and/or fixtures. Microsoft Graph live path uses `/v1.0/subscribedSkus` (not metered beta cloudLicensing). Slack message bodies and Gmail bodies are not retrieved.
"""


def strip_forbidden(text: str) -> tuple[str, list[str]]:
    hits: list[str] = []
    cleaned = text
    for word, pattern in WORD_RE.items():
        if pattern.search(cleaned):
            hits.append(word)
            if word == "compliance":
                cleaned = pattern.sub("control mapping", cleaned)
            elif word in {"attestation", "certified"}:
                cleaned = pattern.sub("observation", cleaned)
            elif word in {"secure", "guaranteed", "guarantees"}:
                cleaned = pattern.sub("observed", cleaned)
    return cleaned, hits


def generate(
    *,
    tenant: str = "m365",
    tenant_name: str | None = None,
    output: Path | None = None,
    snapshot: dict[str, Any] | None = None,
) -> ReportFiles:
    name = tenant_name or f"{tenant}-demo"
    snap = snapshot or load_fixture(tenant)
    framework = {
        "m365": "cis-m365",
        "gws": "cis-gws",
        "github": "iso-27001",
        "slack": "nist-800-53",
        "okta": "nist-800-53",
    }.get(tenant, "iso-27001")
    drift = [d.model_dump() for d in diff_tenant(tenant=tenant, tenant_name=name, current=snap)]
    oauth = [g.model_dump() for g in list_grants(tenant=tenant, tenant_name=name)]
    refs = [r.model_dump() for r in map_tenant(framework=framework, tenant=tenant, tenant_name=name, snapshot=snap)]
    ctx = {
        "display_name": snap.get("display_name") or name,
        "tenant_type": tenant,
        "tenant_name": name,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "version": __version__,
        "scanner": snap.get("scanner") or "fixture",
        "honest_gap": snap.get("honest_gap") or "",
        "settings": snap.get("settings") or [],
        "drift": drift,
        "oauth": oauth,
        "control_refs": refs,
        "apps": snap.get("apps") or [],
    }
    body = _render_markdown(ctx)
    body, hits = strip_forbidden(body)
    body = append_to(body)
    body = scrub_text(body)
    dest = Path(output) if output else Path("output/sspm/report.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    json_path = dest.with_suffix(".json")
    payload = {
        **ctx,
        "title": "Configuration & Inventory Report",
        "sha256": digest,
        "disclaimer": show().text,
        "forbidden_hits": hits,
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    html_path = dest.with_suffix(".html")
    html = _to_html(body, digest)
    html_path.write_text(html, encoding="utf-8")
    return ReportFiles(
        markdown=str(dest),
        json_path=str(json_path),
        html=str(html_path),
        sha256=digest,
        forbidden_hits=hits,
    )


def _to_html(markdown: str, digest: str) -> str:
    escaped = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Configuration &amp; Inventory Report</title>
<style>
body {{ font-family: ui-sans-serif, system-ui, sans-serif; max-width: 880px; margin: 2rem auto; color: #0f172a; background: #f8fafc; }}
pre {{ white-space: pre-wrap; background: #fff; padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px; }}
.meta {{ color: #64748b; font-size: 0.85rem; }}
</style></head><body>
<p class="meta">SHA-256 {digest}</p>
<pre>{escaped}</pre>
</body></html>
"""
