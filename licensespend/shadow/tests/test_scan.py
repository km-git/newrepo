from licensespend.constants import EXAMPLES
from licensespend.shadow.service import scan


def test_shadow_flags_expense_and_spf() -> None:
    report = scan(EXAMPLES / "shadow")
    names = {app.name.lower() for app in report.apps}
    assert any("notion" in n for n in names)
    assert any(
        "spf" in app.source or "include" in (app.note or "").lower() or app.source == "spf-include"
        for app in report.apps
    )
    m365 = next(app for app in report.apps if app.name.lower().startswith("microsoft") and app.source == "expense-csv")
    assert m365.in_pricebook is True
    notion = next(app for app in report.apps if "notion" in app.name.lower() and app.source == "expense-csv")
    assert notion.in_pricebook is False
    assert report.honest_gap
