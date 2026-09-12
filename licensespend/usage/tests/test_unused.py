from datetime import date

from licensespend.constants import EXAMPLES
from licensespend.usage.service import unused_seats


def test_unused_golden_math() -> None:
    report = unused_seats(fixture_root=EXAMPLES, idle_days=90, as_of=date(2026, 9, 7))
    e3 = [r for r in report.rows if r.sku == "m365-e3"]
    slack = [r for r in report.rows if r.sku == "slack-business-plus"]
    github = [r for r in report.rows if r.sku == "github-team"]
    assert len(e3) == 3
    assert len(slack) == 1
    assert len(github) == 1
    assert report.reclaim_monthly_aud == 3 * 36.0 + 15.0 + 4.0
    assert all(r.email is None for r in report.rows)
