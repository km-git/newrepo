"""Report writer with Jinja2 templates and liability disclaimer."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

from sspm.constants import FORBIDDEN_REPORT_WORDS
from sspm.disclaimers.service import load_disclaimer

TEMPLATE = """# Configuration & Inventory Report

**Tenant:** {{ tenant }}
**Generated:** {{ generated_at }}
**Report type:** Configuration & Inventory Report (read-only posture observation)

---

## 1. Tenant Inventory

{{ inventory_summary }}

## 2. Configuration Drift

{% for item in drift %}
- **{{ item.setting_name }}**: `{{ item.old_value }}` → `{{ item.new_value }}` (source: {{ item.change_source }})
{% else %}
No drift detected against baseline.
{% endfor %}

## 3. OAuth Grants

| App | Publisher | Scopes | Risk |
|-----|-----------|--------|------|
{% for g in oauth_grants %}
| {{ g.app_name }} | {{ g.publisher }} | {{ g.scopes }} | {{ g.risk_level }} |
{% endfor %}

## 4. Control References

{% for ref in control_references %}
- **{{ ref.control_id }}**: {{ ref.control_reference }} (framework: {{ ref.framework }})
{% else %}
No control references mapped.
{% endfor %}

---

{{ disclaimer }}
"""


def _scrub(text: str) -> str:
    for word in FORBIDDEN_REPORT_WORDS:
        text = re.sub(rf"\b{word}\b", "posture observation", text, flags=re.IGNORECASE)
    return text


def generate(
    tenant: str,
    output: str | Path,
    *,
    inventory: dict[str, Any] | None = None,
    drift: list[dict[str, Any]] | None = None,
    oauth_grants: list[dict[str, Any]] | None = None,
    control_references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    disclaimer = load_disclaimer("disclaimer_au")
    inventory_summary = json.dumps(
        {"tenant": tenant, "status": "demo", "keys": sorted((inventory or {}).keys())},
        indent=2,
    )
    md = Template(TEMPLATE, autoescape=True).render(
        tenant=tenant,
        generated_at=generated_at,
        inventory_summary=inventory_summary,
        drift=drift or [],
        oauth_grants=oauth_grants or [],
        control_references=control_references or [],
        disclaimer=disclaimer,
    )
    md = _scrub(md)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    json_out = out.with_suffix(".json")
    safe_payload = {
        "report_type": "configuration_and_inventory",
        "tenant": tenant,
        "generated_at": generated_at,
        "inventory_key_count": len(inventory or {}),
        "drift_count": len(drift or []),
        "oauth_grant_count": len(oauth_grants or []),
        "control_reference_count": len(control_references or []),
        "disclaimer_included": True,
    }
    json_out.write_text(json.dumps(safe_payload, indent=2), encoding="utf-8")
    return {"markdown": str(out), "json": str(json_out), "pages_estimate": 5}
