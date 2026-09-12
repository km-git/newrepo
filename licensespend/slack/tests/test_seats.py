from licensespend.constants import EXAMPLES
from licensespend.slack.service import load_fixture


def test_slack_two_guests() -> None:
    report = load_fixture(EXAMPLES / "slack")
    assert report.guests == 2
    paid = [s for s in report.seats if s.role == "member"]
    assert len(paid) >= 1
    assert all(s.sku.startswith("slack") for s in report.seats)
