"""cost/loop — extends forum-watcher; does not duplicate it."""

from __future__ import annotations

import hashlib
import importlib.util
from datetime import UTC, datetime
from typing import Any

import yaml

from cost.db.store import fetch_all, init_schema
from cost.fixtures import tenant_id
from cost.paths import MONTHLY_DIR, PACKAGE_ROOT, REPO_ROOT, ensure_output

COST_CONTEXT = """
Cost context (for vendor and OSS-tool sources only):
- FinOps = Financial Operations, the practice of managing cloud spend (FinOps Foundation)
- CSPM = Cloud Security Posture Management (Wiz, Orca, Prisma Cloud) — NOT this build's focus
- Prowler = open-source cloud configuration scanner, Apache-2.0, v5.41.0 in Sep 2026
- Steampipe = SQL over cloud APIs, AGPL-3.0, must be used as CLI subprocess only
- Cloud Custodian = policy-as-code, Apache-2.0, supports AWS/Azure/GCP/Kubernetes
- c7n-org = multi-account runner for Cloud Custodian, Apache-2.0
- AWS Cost Explorer = free with customer's own AWS account
- Azure Cost Management = free with customer's own Azure subscription
- GCP Cloud Billing = free with customer's own GCP project
- Trivy = IaC + image + secret scanner, v0.71.2 (avoid v0.69.4 — CVE-2026-33634)

Module hint bias: {module_hint}
If module_hint contains "cost" or one of the 10 module names, lock module-fit to the matching module.

Disallowed report language: "compliance", "attestation", "certified", "secure", "guaranteed". Use "cost observation", "configuration reference", "framework reference" instead.
"""

COST_MODULES = (
    "audit",
    "aws_inventory",
    "azure_inventory",
    "gcp_inventory",
    "cost_explorer",
    "rightsizing",
    "untagged",
    "config_drift",
    "compliance_map",
    "report_writer",
)


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def load_watch():
    path = REPO_ROOT / "forum-watcher" / "scripts" / "watch.py"
    spec = importlib.util.spec_from_file_location("forum_watch", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify_with_cost_context(item: dict[str, Any]) -> dict[str, Any]:
    watch = load_watch()
    hint = str(item.get("module_hint") or "")
    result = watch.classify(item)
    blob = f"{item.get('title', '')} {item.get('summary', '')} {hint}".lower()
    for name in COST_MODULES:
        token = name.replace("_", " ")
        if (name in hint or name in blob or token in blob or "cost" in hint) and ("cost" in hint or name in hint):
            result["module"] = name if name in hint or name in blob or token in blob else result.get("module")
            break
    result["cost_context_attached"] = True
    result["prompt_suffix"] = COST_CONTEXT.format(module_hint=hint or "cost")[:200]
    return result


def extra_sources() -> list[dict[str, Any]]:
    path = PACKAGE_ROOT / "loop" / "sources.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return list(data)


def run(*, sandbox: bool = True, monthly: bool = False, **_kwargs: Any) -> dict[str, Any]:
    ensure_output()
    if monthly:
        return monthly_rollup()
    sources = extra_sources()
    sample = {
        "title": "Prowler 5.41.0 release notes for cloud configuration snapshots",
        "summary": "CLI JSON output directory for cost-relevant config snapshots",
        "source": "prowler releases",
        "module_hint": "config_drift, cost",
        "url": "https://github.com/prowler-cloud/prowler/releases",
    }
    classified = classify_with_cost_context(sample)
    discover_dir = PACKAGE_ROOT / "loop" / "discoveries"
    discover_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    note = discover_dir / f"{today}.md"
    if classified.get("verdict") == "discover" or classified.get("score", 0) >= 5:
        note.write_text(
            f"# Cost discoveries — {today}\n\n"
            f"- [x] **[{classified.get('module')}]** [{sample['title']}]({sample['url']})\n",
            encoding="utf-8",
        )
    return {
        "ok": True,
        "sources": len(sources),
        "sample_verdict": classified.get("verdict"),
        "sample_module": classified.get("module"),
        "sandbox": sandbox,
        "watcher_imported": True,
    }


def monthly_rollup() -> dict[str, Any]:
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    stamp = now.strftime("%Y-%m")
    conn = init_schema()
    tid = tenant_id()
    costs = fetch_all(conn, "findings_costs", tid)
    rightsizing = fetch_all(conn, "findings_rightsizing", tid)
    untagged = fetch_all(conn, "findings_untagged", tid)
    spend = round(sum(float(r.get("amount") or 0) for r in costs), 2)
    savings = round(sum(float(r.get("monthly_savings_estimate") or 0) for r in rightsizing), 2)
    untagged_n = len(untagged)
    month_md = MONTHLY_DIR / f"{stamp}.md"
    trend_md = MONTHLY_DIR / "cost-trend.md"
    month_body = (
        f"# Monthly cost rollup — {stamp}\n\n"
        f"- Spend observed: USD {spend:.2f}\n"
        f"- Heuristic rightsizing savings still open: USD {savings:.2f}\n"
        f"- Untagged resource count: {untagged_n}\n\n"
        "First Monday 09:00 AEST compound slot. Mapping only; not an attestation.\n"
    )
    trend_body = (
        f"# Cost trend\n\n"
        f"Generated {now.replace(microsecond=0).isoformat()}.\n\n"
        f"| Metric | Value |\n| --- | --- |\n"
        f"| Monthly spend observed | {spend:.2f} |\n"
        f"| Open rightsizing estimate | {savings:.2f} |\n"
        f"| Untagged resource count | {untagged_n} |\n\n"
        "Is monthly spend decreasing? Compare this file across months. "
        "Are rightsizing recommendations being applied? Only after engineering review. "
        "Is the untagged-resource count dropping? That is an organisational metric.\n"
    )
    month_md.write_text(month_body, encoding="utf-8")
    trend_md.write_text(trend_body, encoding="utf-8")
    return {"ok": True, "month": str(month_md), "trend": str(trend_md), "spend": spend}
