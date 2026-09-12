from licensespend.constants import EXAMPLES
from licensespend.github.service import load_fixture


def test_github_one_outside_collaborator() -> None:
    report = load_fixture(EXAMPLES / "github")
    assert report.outside_collaborators == 1
    assert any(s.role == "outside_collaborator" for s in report.seats)
    unused = [
        s
        for s in report.seats
        if s.role == "member" and s.last_active and s.last_active.year <= 2026 and s.last_active.month <= 3
    ]
    assert unused
