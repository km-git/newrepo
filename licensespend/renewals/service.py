"""Contract calendar from contracts.yaml. ICS-optional. Nudge copy is a draft."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import yaml

from licensespend.constants import CONTRACTS
from licensespend.renewals.models import Contract, RenewalItem, RenewalReport


def load_contracts(path: Path | None = None) -> list[Contract]:
    payload = yaml.safe_load((path or CONTRACTS).read_text(encoding="utf-8")) or {}
    return [Contract.model_validate(row) for row in payload.get("contracts") or []]


def upcoming(
    *,
    days: int = 60,
    as_of: date | None = None,
    contracts_path: Path | None = None,
) -> RenewalReport:
    as_of = as_of or date.today()
    horizon = as_of + timedelta(days=days)
    items: list[RenewalItem] = []
    for contract in load_contracts(contracts_path):
        if as_of <= contract.renew_on <= horizon:
            notice_by = contract.renew_on - timedelta(days=contract.notice_days)
            items.append(
                RenewalItem(
                    vendor=contract.vendor,
                    seats=contract.seats,
                    renew_on=contract.renew_on,
                    notice_by=notice_by,
                    amount_aud=contract.amount_aud,
                    days_until=(contract.renew_on - as_of).days,
                    nudge=(
                        f"Draft: remind {contract.vendor} owner that renewal on "
                        f"{contract.renew_on.isoformat()} needs notice by {notice_by.isoformat()}."
                    ),
                )
            )
    items.sort(key=lambda item: item.renew_on)
    return RenewalReport(as_of=as_of, window_days=days, upcoming=items)


def to_ics(report: RenewalReport) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//licensespend//renewals//EN",
    ]
    for item in report.upcoming:
        stamp = item.renew_on.strftime("%Y%m%d")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"DTSTART;VALUE=DATE:{stamp}",
                f"SUMMARY:{item.vendor} license renewal (draft)",
                f"DESCRIPTION:{item.nudge}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"
