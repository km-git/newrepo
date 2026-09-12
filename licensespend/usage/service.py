"""Join assigned vs last-active across M365 / Slack / GitHub. DuckDB view v_unused_seats."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import yaml

from licensespend.constants import EXAMPLES, PRICEBOOK, include_email
from licensespend.github.service import load_fixture as load_github
from licensespend.m365.service import load_fixture as load_m365
from licensespend.seats import Seat
from licensespend.slack.service import load_fixture as load_slack
from licensespend.usage.models import PriceSku, UnusedReport, UnusedSeat


def load_pricebook(path: Path | None = None) -> dict[str, PriceSku]:
    payload = yaml.safe_load((path or PRICEBOOK).read_text(encoding="utf-8")) or {}
    skus = {}
    for row in payload.get("skus") or []:
        sku = PriceSku.model_validate(row)
        skus[sku.id] = sku
    return skus


def _collect_seats(fixture_root: Path) -> list[Seat]:
    root = Path(fixture_root)
    seats: list[Seat] = []
    if (root / "m365").is_dir():
        seats.extend(load_m365(root / "m365").seats)
    if (root / "slack").is_dir():
        seats.extend(load_slack(root / "slack").seats)
    if (root / "github").is_dir():
        seats.extend(load_github(root / "github").seats)
    google = root / "google"
    if google.is_dir() and (google / "users.json").is_file():
        import json

        from licensespend.m365.service import parse_users

        extra = parse_users(json.loads((google / "users.json").read_text(encoding="utf-8")))
        for seat in extra:
            seats.append(seat.model_copy(update={"vendor": "google"}))
    return seats


def unused_seats(
    *,
    fixture_root: Path | None = None,
    idle_days: int = 90,
    as_of: date | None = None,
    pricebook_path: Path | None = None,
) -> UnusedReport:
    as_of = as_of or date.today()
    prices = load_pricebook(pricebook_path)
    seats = _collect_seats(Path(fixture_root) if fixture_root else EXAMPLES)
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE seats (
            user_id VARCHAR,
            sku VARCHAR,
            vendor VARCHAR,
            last_active DATE,
            department VARCHAR,
            role VARCHAR,
            assigned BOOLEAN,
            email_hash VARCHAR,
            email VARCHAR,
            note VARCHAR,
            monthly_cost DOUBLE
        )
        """
    )
    abstained: list[str] = []
    rows = []
    for seat in seats:
        price = prices.get(seat.sku)
        if price is None:
            abstained.append(seat.sku)
            cost = 0.0
        else:
            cost = float(price.monthly_aud)
        rows.append(
            (
                seat.user_id,
                seat.sku,
                seat.vendor,
                seat.last_active,
                seat.department,
                seat.role,
                seat.assigned,
                seat.email_hash,
                seat.email if include_email() else None,
                seat.note,
                cost,
            )
        )
    con.executemany("INSERT INTO seats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    as_of_sql = as_of.isoformat()
    if as_of_sql != as_of.strftime("%Y-%m-%d"):
        raise ValueError("as_of must be a calendar date")
    threshold = int(idle_days)
    # CREATE VIEW cannot take prepared parameters in DuckDB; as_of is ISO date, threshold is int.
    con.execute(
        f"""
        CREATE VIEW v_unused_seats AS
        SELECT
            user_id,
            sku,
            vendor,
            last_active,
            department,
            role,
            email_hash,
            email,
            note,
            monthly_cost,
            CASE
                WHEN last_active IS NULL THEN {threshold}
                ELSE date_diff('day', last_active, DATE '{as_of_sql}')
            END AS idle_days
        FROM seats
        WHERE assigned
          AND (
            last_active IS NULL
            OR date_diff('day', last_active, DATE '{as_of_sql}') >= {threshold}
          )
        """
    )
    fetched = con.execute(
        """
        SELECT user_id, sku, vendor, idle_days, monthly_cost, department, role,
               email_hash, email, note, last_active
        FROM v_unused_seats
        ORDER BY monthly_cost DESC, user_id
        """
    ).fetchall()
    unused = [
        UnusedSeat(
            user_id=row[0],
            sku=row[1],
            vendor=row[2],
            idle_days=int(row[3]) if row[3] is not None else None,
            monthly_cost=float(row[4] or 0),
            department=row[5],
            role=row[6] or "member",
            email_hash=row[7],
            email=row[8],
            note=row[9] or ("signin unknown / lag; unused not never" if row[10] is None else None),
            last_active=row[10],
        )
        for row in fetched
    ]
    reclaim = round(sum(item.monthly_cost for item in unused), 2)
    return UnusedReport(
        as_of=as_of,
        idle_days_threshold=idle_days,
        unused_count=len(unused),
        reclaim_monthly_aud=reclaim,
        rows=unused,
        abstained=sorted(set(abstained)),
    )
