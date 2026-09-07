from dspm.classification.recognizers import check_custom_type
from dspm.exposure.service import scan_exposure
from dspm.remediation.service import build_plan


def test_custom_type_au_tfn():
    result = check_custom_type("au_tfn", "My TFN is 123 456 789")
    assert result["match"] is True


def test_exposure_scan_fixture():
    findings = scan_exposure("aws")
    assert len(findings) >= 1


def test_remediation_plan_dry_run():
    plan = build_plan(dry_run=True)
    assert len(plan) == 4
    assert all(p["dry_run_safe"] for p in plan)
