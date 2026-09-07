"""Build HTML + Markdown + JSON reclaim pack with SHA-256 watermark."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from licensespend.constants import EXAMPLES, include_email
from licensespend.privacy import contains_raw_email
from licensespend.renewals.service import upcoming
from licensespend.report.models import ReportFiles, ReportPayload
from licensespend.seats import Seat
from licensespend.shadow.service import scan as scan_shadow
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


def build(
    *,
    client: str,
    out_dir: Path,
    fixture_root: Path | None = None,
    as_of: date | None = None,
    idle_days: int = 90,
) -> ReportFiles:
    as_of = as_of or date(2026, 9, 7)
    root = Path(fixture_root) if fixture_root else EXAMPLES
    unused = unused_seats(fixture_root=root, idle_days=idle_days, as_of=as_of)
    seats = _collect_seats(root)
    unused_ids = {row.user_id for row in unused.rows}
    bought, used = _counts(seats, unused_ids=unused_ids)
    renewals = upcoming(days=60, as_of=as_of)
    shadow = scan_shadow(root / "shadow" if (root / "shadow").is_dir() else root)

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
        reclaim_monthly_aud=unused.reclaim_monthly_aud,
        renewals=[item.model_dump(mode="json") for item in renewals.upcoming],
        shadow_apps=[app.model_dump(mode="json") for app in shadow.apps],
        reclaim_appendix=appendix,
    )
    dumped = payload.model_dump(mode="json")
    if not include_email():
        for row in dumped["unused"]:
            row["email"] = None
    watermark = _watermark(dumped)
    dumped["watermark"] = watermark
    payload.watermark = watermark

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
        "client": client,
        "as_of": as_of.isoformat(),
        "reclaim_monthly_aud": unused.reclaim_monthly_aud,
        "unused_count": unused.unused_count,
        "seats_bought": bought,
        "seats_used": used,
        "unused": dumped["unused"],
        "renewals": dumped["renewals"],
        "shadow_apps": dumped["shadow_apps"],
        "watermark": watermark,
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
        watermark=watermark,
        client=client,
        reclaim_monthly_aud=unused.reclaim_monthly_aud,
        unused_count=unused.unused_count,
        emails_included=include_email(),
    )


def verify_watermark(json_path: Path) -> bool:
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    claimed = payload.get("watermark")
    return claimed == _watermark(payload)
