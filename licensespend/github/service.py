"""GitHub org seats, outside collaborators, unused members.

Fixtures: examples/github/members.json + audit_log.json.
Primary extra: PyGithub (LGPL-3.0) — leaf dependency, never vendored.

Honest gap: contribution stats are incomplete without the audit log;
never clone private repos for this product.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from licensespend.privacy import hash_email
from licensespend.seats import Seat, SeatReport


def _parse_date(raw: object) -> date | None:
    if raw is None or raw == "":
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def parse_members(payload: dict) -> list[Seat]:
    rows = payload.get("members") or payload.get("users") or []
    seats: list[Seat] = []
    for row in rows:
        user_id = str(row.get("login") or row.get("user_id") or row.get("id") or "")
        if not user_id:
            continue
        role = str(row.get("role") or "member")
        outside = role in {"outside_collaborator", "outside"}
        email = row.get("email")
        seats.append(
            Seat(
                user_id=user_id,
                sku="github-outside" if outside else "github-team",
                vendor="github",
                last_active=_parse_date(row.get("last_active")),
                department=row.get("department"),
                role="outside_collaborator" if outside else "member",
                assigned=True,
                email_hash=hash_email(email) if email else None,
                email=str(email) if email else None,
                note="contribution stats incomplete without audit log; never clone private repos",
            )
        )
    return seats


def apply_audit_log(seats: list[Seat], payload: dict) -> list[Seat]:
    events = payload.get("events") or payload.get("audit_log") or []
    latest: dict[str, date] = {}
    for event in events:
        actor = str(event.get("actor") or event.get("user") or "")
        when = _parse_date(event.get("created_at") or event.get("timestamp"))
        if not actor or when is None:
            continue
        if actor not in latest or when > latest[actor]:
            latest[actor] = when
    updated: list[Seat] = []
    for seat in seats:
        last = latest.get(seat.user_id) or seat.last_active
        updated.append(seat.model_copy(update={"last_active": last}))
    return updated


def load_fixture(fixture_dir: Path) -> SeatReport:
    directory = Path(fixture_dir)
    members_path = directory / "members.json"
    audit_path = directory / "audit_log.json"
    members_payload = (
        json.loads(members_path.read_text(encoding="utf-8")) if members_path.is_file() else {"members": []}
    )
    seats = parse_members(members_payload)
    if audit_path.is_file():
        seats = apply_audit_log(seats, json.loads(audit_path.read_text(encoding="utf-8")))
    return SeatReport(
        vendor="github",
        seats=seats,
        outside_collaborators=sum(1 for s in seats if s.role == "outside_collaborator"),
        honest_gap="Contribution stats are incomplete without audit log; never clone private repos.",
    )
