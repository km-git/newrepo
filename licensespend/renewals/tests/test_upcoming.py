from datetime import date

from licensespend.renewals.service import upcoming


def test_upcoming_returns_microsoft365_within_60_days() -> None:
    report = upcoming(days=60, as_of=date(2026, 9, 7))
    vendors = {item.vendor for item in report.upcoming}
    assert "microsoft365" in vendors
    assert all("Draft:" in item.nudge for item in report.upcoming)
