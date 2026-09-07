"""HTML rendering for detailed tape-to-cloud sample reports."""

from __future__ import annotations

import html
import json
from typing import Any

from tape_to_cloud.catalog import LAYER_CATALOG, LAYERS

_SKIP_RESULT_KEYS = {
    "executive_summary",
    "kpis",
    "recommendations",
    "chain_of_custody",
}


def _esc(value: Any) -> str:
    return html.escape(str(value))


def render_kpis(kpis: list[dict[str, Any]]) -> str:
    if not kpis:
        return ""
    tiles = "".join(
        f'<div class="kpi"><div class="kpi-label">{_esc(row["label"])}</div>'
        f'<div class="kpi-value">{_esc(row["value"])}</div></div>'
        for row in kpis
    )
    return f'<div class="kpis">{tiles}</div>'


def render_table(rows: list[dict[str, Any]], caption: str = "") -> str:
    if not rows:
        return ""
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    head = "".join(f"<th>{_esc(k)}</th>" for k in keys)
    body = []
    for row in rows:
        cells = "".join(f"<td>{_esc(row.get(k, ''))}</td>" for k in keys)
        risk = str(row.get("risk_band") or row.get("risk") or row.get("status") or "").lower()
        cls = ""
        if risk in {"critical", "high"}:
            cls = ' class="risk-high"'
        elif risk in {"moderate"}:
            cls = ' class="risk-mid"'
        body.append(f"<tr{cls}>{cells}</tr>")
    cap = f"<caption>{_esc(caption)}</caption>" if caption else ""
    return f"<table>{cap}<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _render_scalar_map(data: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in data.items() if not isinstance(v, (dict, list))
    )
    nested = []
    for key, value in data.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            nested.append(f"<h3>{_esc(key)}</h3>{render_table(value, key)}")
        elif isinstance(value, dict):
            nested.append(f"<h3>{_esc(key)}</h3>{_render_scalar_map(value)}")
        elif isinstance(value, list):
            nested.append(f"<h3>{_esc(key)}</h3><p>{_esc(', '.join(str(x) for x in value))}</p>")
    table = f'<table class="kv"><tbody>{rows}</tbody></table>' if rows else ""
    return table + "".join(nested)


def render_result_sections(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in result.items():
        if key in _SKIP_RESULT_KEYS:
            continue
        title = key.replace("_", " ")
        if isinstance(value, list) and value and isinstance(value[0], dict):
            parts.append(f"<h3>{_esc(title)}</h3>{render_table(value, title)}")
        elif isinstance(value, dict):
            parts.append(f"<h3>{_esc(title)}</h3>{_render_scalar_map(value)}")
        elif isinstance(value, list):
            parts.append(f"<h3>{_esc(title)}</h3><p>{_esc(', '.join(str(x) for x in value))}</p>")
        else:
            parts.append(f"<h3>{_esc(title)}</h3><p>{_esc(value)}</p>")
    return "".join(parts)


def render_layers_grid(layers: dict[str, Any]) -> str:
    cards = []
    for lid in LAYERS:
        spec = LAYER_CATALOG[lid]
        payload = layers.get(lid) or {}
        items = "".join(f"<li><strong>{_esc(k)}</strong>: {_esc(v)}</li>" for k, v in payload.items())
        cards.append(
            f'<div class="layer-card"><h3>{_esc(spec["title"])}</h3><code>{_esc(lid)}</code><ul>{items}</ul></div>'
        )
    return f'<div class="layer-grid">{"".join(cards)}</div>'


def render_coc(events: list[dict[str, str]]) -> str:
    if not events:
        return ""
    items = "".join(
        f"<li><code>{_esc(e.get('utc', ''))}</code> — {_esc(e.get('event', ''))} "
        f"<span class='muted'>({_esc(e.get('actor', ''))})</span></li>"
        for e in events
    )
    return f"<ol class='coc'>{items}</ol>"


def render_citations(citations: list[dict[str, str]]) -> str:
    if not citations:
        return ""
    items = "".join(
        f'<li><a href="{_esc(c["url"])}">{_esc(c["title"])}</a> — {_esc(c["fields"])}</li>' for c in citations
    )
    return f"<ul class='citations'>{items}</ul>"


def render_detailed_report(report: dict[str, Any], json_href: str) -> str:
    """Body HTML (no shell) for a module or job-pack report."""
    if report.get("kind") == "sample-job-pack":
        return _render_job_pack(report, json_href)
    kpis = render_kpis(report.get("kpis") or [])
    recs = report.get("recommendations") or []
    rec_html = "".join(f"<li>{_esc(r)}</li>" for r in recs)
    payload = html.escape(json.dumps(report, indent=2, default=str))
    return f"""
    <section>
      <p class="pill">sample report</p>
      <h2>{_esc(report.get("menu", report.get("report_id")))}</h2>
      <p><code>{_esc(report.get("report_id"))}</code> · job <code>{_esc(report.get("job_id"))}</code>
         · {_esc(report.get("customer"))}</p>
      <p class="muted">{_esc(report.get("disclaimer", ""))}</p>
      <p>{_esc(report.get("executive_summary", ""))}</p>
      {kpis}
      <p><a href="{_esc(json_href)}">Raw JSON</a></p>
    </section>
    <section>
      <h2>Findings</h2>
      {render_result_sections(report.get("result") or {})}
    </section>
    <section>
      <h2>Chain of custody</h2>
      {render_coc(report.get("chain_of_custody") or [])}
    </section>
    <section>
      <h2>Recommendations</h2>
      <ul>{rec_html}</ul>
    </section>
    <section>
      <h2>Six layers (called on this module)</h2>
      {render_layers_grid(report.get("layers") or {})}
    </section>
    <section>
      <h2>Research basis</h2>
      {render_citations(report.get("citations") or [])}
    </section>
    <section>
      <h2>Machine-readable copy</h2>
      <details><summary>JSON</summary><pre>{payload}</pre></details>
    </section>
    """


def _render_job_pack(report: dict[str, Any], json_href: str) -> str:
    kpis = render_kpis(report.get("kpis") or [])
    items = []
    for row in report.get("index") or []:
        items.append(
            "<tr>"
            f"<td><code>{_esc(row.get('module'))}</code></td>"
            f"<td>{_esc(row.get('menu'))}</td>"
            f'<td><a href="{_esc(row.get("href"))}">{_esc(row.get("report_id"))}</a></td>'
            f"<td>{_esc(row.get('headline'))}</td></tr>"
        )
    table = (
        "<table><thead><tr><th>Module</th><th>Menu</th><th>Report</th><th>Headline</th></tr></thead>"
        f"<tbody>{''.join(items)}</tbody></table>"
    )
    return f"""
    <section>
      <p class="pill">job pack</p>
      <h2>{_esc(report.get("menu", "Job pack"))}</h2>
      <p><code>{_esc(report.get("report_id"))}</code> · {_esc(report.get("customer"))}</p>
      <p>{_esc(report.get("executive_summary", ""))}</p>
      {kpis}
      <p><a href="{_esc(json_href)}">Raw JSON (all 16 reports)</a></p>
    </section>
    <section>
      <h2>Module reports</h2>
      {table}
    </section>
    <section>
      <h2>Research basis</h2>
      {render_citations(report.get("citations") or [])}
    </section>
    """
