"""Build HTML + Markdown + JSON reclaim pack with SHA-256 watermark."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from licensespend.constants import (
    CONTRACTS,
    HONEST_GAPS,
    include_email,
    resolve_fixture_root,
)
from licensespend.privacy import contains_raw_email
from licensespend.renewals.service import upcoming
from licensespend.report.models import ReportFiles, ReportPayload
from licensespend.seats import Seat
from licensespend.shadow.service import scan as scan_shadow
from licensespend.usage.models import UnusedReport
from licensespend.usage.service import _collect_seats, unused_seats

TEMPLATES = Path(__file__).resolve().parent / "templates"


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _watermark(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "watermark"}
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def _counts(seats: list[Seat], *, unused_ids: set[str]) -> tuple[dict[str, int], dict[str, int]]:
    bought: dict[str, int] = {}
    used: dict[str, int] = {}
    for seat in seats:
        bought[seat.sku] = bought.get(seat.sku, 0) + 1
        if seat.user_id not in unused_ids:
            used[seat.sku] = used.get(seat.sku, 0) + 1
        else:
            used.setdefault(seat.sku, 0)
    return bought, used


def _idle_days(seat: Seat, as_of: date) -> int | None:
    if seat.last_active is None:
        return None
    return (as_of - seat.last_active).days


def idle_buckets(seats: list[Seat], as_of: date) -> dict[str, int]:
    buckets = {"0-29": 0, "30-59": 0, "60-89": 0, "90+": 0, "unknown": 0}
    for seat in seats:
        if not seat.assigned:
            continue
        days = _idle_days(seat, as_of)
        if days is None:
            buckets["unknown"] += 1
        elif days < 30:
            buckets["0-29"] += 1
        elif days < 60:
            buckets["30-59"] += 1
        elif days < 90:
            buckets["60-89"] += 1
        else:
            buckets["90+"] += 1
    return buckets


def _vendor_breakdown(unused: UnusedReport) -> list[dict]:
    by: dict[str, dict] = {}
    for row in unused.rows:
        rec = by.setdefault(
            row.vendor,
            {"vendor": row.vendor, "unused_seats": 0, "monthly_aud": 0.0, "skus": {}},
        )
        rec["unused_seats"] += 1
        rec["monthly_aud"] = round(float(rec["monthly_aud"]) + row.monthly_cost, 2)
        skus = rec["skus"]
        skus[row.sku] = int(skus.get(row.sku, 0)) + 1
    return sorted(by.values(), key=lambda item: (-item["monthly_aud"], item["vendor"]))


def _department_breakdown(unused: UnusedReport) -> list[dict]:
    by: dict[str, dict] = {}
    for row in unused.rows:
        dept = row.department or "unassigned"
        rec = by.setdefault(dept, {"department": dept, "unused_seats": 0, "monthly_aud": 0.0})
        rec["unused_seats"] += 1
        rec["monthly_aud"] = round(float(rec["monthly_aud"]) + row.monthly_cost, 2)
    return sorted(by.values(), key=lambda item: (-item["monthly_aud"], item["department"]))


def _qbr_talk_track(
    *,
    client: str,
    as_of: date,
    unused: UnusedReport,
    renewals: list,
    shadow_apps: list,
) -> list[str]:
    vendors = sorted({row.vendor for row in unused.rows})
    annual = round(unused.reclaim_monthly_aud * 12, 2)
    lines = [
        (
            f"Draft QBR talk-track for {client} as of {as_of.isoformat()}: "
            f"{unused.unused_count} unused seats"
            + (f" across {', '.join(vendors)}" if vendors else "")
            + f" = A${unused.reclaim_monthly_aud:.2f}/month "
            f"(A${annual:.2f}/year at operator list price)."
        ),
        "This is a spend report for human review. Do not auto-revoke seats.",
    ]
    if unused.rows:
        top = unused.rows[0]
        lines.append(
            f"Highest-cost unused seat: {top.sku} ({top.vendor}) at A${top.monthly_cost:.2f}/month, "
            f"idle {top.idle_days} days (hashed id {top.user_id})."
        )
    if renewals:
        names = ", ".join(f"{item.vendor} {item.renew_on.isoformat()}" for item in renewals)
        lines.append(f"Renewals inside the 60-day window: {names}.")
    else:
        lines.append("No contract renewals fall inside the 60-day window.")
    shadow_hits = [app.name for app in shadow_apps if not app.in_pricebook]
    if shadow_hits:
        lines.append("Possible shadow SaaS (not in pricebook): " + ", ".join(shadow_hits[:8]) + ".")
    lines.append(
        "Action: walk the draft reclaim appendix with the tenant owner; dual-gate reclaim records intent only."
    )
    return lines


def _contracts_path(root: Path) -> Path:
    local = root / "contracts.yaml"
    return local if local.is_file() else CONTRACTS


def build_payload(
    *,
    client: str,
    fixture_root: Path | None = None,
    as_of: date | None = None,
    idle_days: int = 90,
) -> ReportPayload:
    as_of = as_of or date(2026, 9, 7)
    root = resolve_fixture_root(client, fixture_root)
    unused = unused_seats(fixture_root=root, idle_days=idle_days, as_of=as_of)
    seats = _collect_seats(root)
    unused_ids = {row.user_id for row in unused.rows}
    bought, used = _counts(seats, unused_ids=unused_ids)
    renewals = upcoming(days=60, as_of=as_of, contracts_path=_contracts_path(root))
    shadow = scan_shadow(root)

    appendix = []
    for row in unused.rows:
        item = {"user_id": row.user_id, "sku": row.sku, "email_hash": row.email_hash}
        if include_email() and row.email:
            item["email"] = row.email
        appendix.append(item)

    payload = ReportPayload(
        client=client,
        as_of=as_of.isoformat(),
        seats_bought=bought,
        seats_used=used,
        unused=[r.model_dump(mode="json") for r in unused.rows],
        unused_count=unused.unused_count,
        seats_total=len(seats),
        idle_days_threshold=idle_days,
        reclaim_monthly_aud=unused.reclaim_monthly_aud,
        reclaim_annual_aud=round(unused.reclaim_monthly_aud * 12, 2),
        vendor_breakdown=_vendor_breakdown(unused),
        department_breakdown=_department_breakdown(unused),
        idle_buckets=idle_buckets(seats, as_of),
        renewals=[item.model_dump(mode="json") for item in renewals.upcoming],
        shadow_apps=[app.model_dump(mode="json") for app in shadow.apps],
        reclaim_appendix=appendix,
        qbr_talk_track=_qbr_talk_track(
            client=client,
            as_of=as_of,
            unused=unused,
            renewals=renewals.upcoming,
            shadow_apps=shadow.apps,
        ),
        honest_gaps=list(HONEST_GAPS),
    )
    dumped = payload.model_dump(mode="json")
    if not include_email():
        for row in dumped["unused"]:
            row["email"] = None
        payload.unused = dumped["unused"]
    watermark = _watermark(dumped)
    payload.watermark = watermark
    return payload


def build(
    *,
    client: str,
    out_dir: Path,
    fixture_root: Path | None = None,
    as_of: date | None = None,
    idle_days: int = 90,
) -> ReportFiles:
    as_of = as_of or date(2026, 9, 7)
    payload = build_payload(
        client=client,
        fixture_root=fixture_root,
        as_of=as_of,
        idle_days=idle_days,
    )
    dumped = payload.model_dump(mode="json")
    dumped["watermark"] = payload.watermark

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{client}-license-spend.json"
    md_path = out / f"{client}-license-spend.md"
    html_path = out / f"{client}-license-spend.html"
    json_path.write_text(_canonical_json(dumped) + "\n", encoding="utf-8")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )
    context = {
        "client": payload.client,
        "as_of": payload.as_of,
        "reclaim_monthly_aud": payload.reclaim_monthly_aud,
        "reclaim_annual_aud": payload.reclaim_annual_aud,
        "unused_count": payload.unused_count,
        "seats_total": payload.seats_total,
        "seats_bought": payload.seats_bought,
        "seats_used": payload.seats_used,
        "unused": payload.unused,
        "renewals": payload.renewals,
        "shadow_apps": payload.shadow_apps,
        "vendor_breakdown": payload.vendor_breakdown,
        "department_breakdown": payload.department_breakdown,
        "idle_buckets": payload.idle_buckets,
        "qbr_talk_track": payload.qbr_talk_track,
        "honest_gaps": payload.honest_gaps,
        "watermark": payload.watermark,
        "disclaimer": payload.disclaimer,
    }
    md_path.write_text(env.get_template("report.md.j2").render(**context), encoding="utf-8")
    html_path.write_text(env.get_template("report.html.j2").render(**context), encoding="utf-8")

    if not include_email():
        for path in (json_path, md_path, html_path):
            text = path.read_text(encoding="utf-8")
            if contains_raw_email(text):
                raise RuntimeError(f"raw email leaked into {path}")

    return ReportFiles(
        json_path=str(json_path),
        markdown_path=str(md_path),
        html_path=str(html_path),
        watermark=payload.watermark,
        client=payload.client,
        reclaim_monthly_aud=payload.reclaim_monthly_aud,
        unused_count=payload.unused_count,
        emails_included=include_email(),
    )


def verify_watermark(json_path: Path) -> bool:
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    claimed = payload.get("watermark")
    return claimed == _watermark(payload)
