"""Slack billed active vs inactive members, guests, unused paid seats.

Fixture: examples/slack/users_list.json (users.list shape).
Do not call conversations.history.

Honest gap: Slack Enterprise Grid org-level billing may need admin APIs
not in the free test token — fixture covers it.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from licensespend.privacy import hash_email
from licensespend.seats import Seat, SeatReport


def _from_epoch(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), tz=timezone.utc).date()
    text = str(value)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_users_list(payload: dict) -> list[Seat]:
    members = payload.get("members") or payload.get("users") or []
    seats: list[Seat] = []
    for row in members:
        if row.get("deleted") or row.get("is_bot") or row.get("id") == "USLACKBOT":
            continue
        user_id = str(row.get("id") or row.get("user_id") or "")
        if not user_id:
            continue
        guest = bool(row.get("is_restricted") or row.get("is_ultra_restricted") or row.get("role") == "guest")
        profile = row.get("profile") if isinstance(row.get("profile"), dict) else {}
        email = row.get("email") or profile.get("email")
        last_active = _from_epoch(row.get("last_active") or row.get("updated"))
        seats.append(
            Seat(
                user_id=user_id,
                sku="slack-guest" if guest else "slack-business-plus",
                vendor="slack",
                last_active=last_active,
                department=row.get("department") or profile.get("title"),
                role="guest" if guest else "member",
                assigned=True,
                email_hash=hash_email(email) if email else None,
                email=str(email) if email else None,
                note="enterprise-grid billing not in free token; fixture covers billed seats",
            )
        )
    return seats


def load_fixture(fixture_dir: Path) -> SeatReport:
    directory = Path(fixture_dir)
    path = directory / "users_list.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"members": []}
    seats = parse_users_list(payload)
    return SeatReport(
        vendor="slack",
        seats=seats,
        guests=sum(1 for s in seats if s.role == "guest"),
        honest_gap="Enterprise Grid org-level billing may need admin APIs not in the free test token.",
    )
