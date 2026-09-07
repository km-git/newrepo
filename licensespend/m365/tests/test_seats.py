from licensespend.constants import EXAMPLES
from licensespend.m365.service import load_fixture


def test_m365_fixture_twelve_e3_three_unused() -> None:
    report = load_fixture(EXAMPLES / "m365")
    e3 = [s for s in report.seats if s.sku == "m365-e3"]
    assert len(e3) == 12
    unused = [s for s in e3 if s.last_active is not None and (date_of() - s.last_active).days >= 90]
    assert len(unused) == 3
    assert all(s.email_hash for s in report.seats if s.email)
    assert report.honest_gap


def date_of():
    from datetime import date

    return date(2026, 9, 7)
