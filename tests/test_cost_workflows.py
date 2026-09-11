"""Integrity checks for cost GitHub workflows and Trivy pin."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"

TRIVY_SHA = "57a97c7e7821a5776cebc9bb87c984fa69cba8f1"
CPR_SHA = "5f6978faf089d4d20b00c7766989d076bb2fc7f1"
APPROVE_SHA = "f0939ea97e9205ef24d872e76833fa908a770363"


def test_cost_ci_has_merge_group_and_trivy_pin():
    text = (WF / "cost-ci.yml").read_text(encoding="utf-8")
    assert "merge_group" in text
    assert f"aquasecurity/trivy-action@{TRIVY_SHA}" in text
    assert "v0.71.2" in text
    assert "v0.69.4" in text  # mentioned as never
    assert "@latest" not in text.split("trivy-action")[0] or "trivy-action@57a97c7e" in text


def test_auto_approve_filters_actors_and_remediation():
    text = (WF / "cost-auto-approve.yml").read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert "pull_request_target" not in text
    assert "dependabot[bot]" in text
    assert "[auto-approved]" in text
    assert f"hmarr/auto-approve-action@{APPROVE_SHA}" in text
    assert "auto-approve-action@v4" not in text
    assert "v4.0.0" in text
    assert "cost/remediation/" in text
    assert "merge_group" in text


def test_watch_cron_is_monday_aest():
    text = (WF / "cost-watch.yml").read_text(encoding="utf-8")
    assert "0 9 * * 1" in text
    assert "Australia/Sydney" in text
    assert f"peter-evans/create-pull-request@{CPR_SHA}" in text
    assert "create-pull-request@v8" not in text
    assert "v8.1.1" in text


def test_keepalive_and_monthly():
    keep = (WF / "cost-keepalive.yml").read_text(encoding="utf-8")
    assert "uses: gautamkrishnar/keepalive-workflow" not in keep
    assert "actions/workflows/" in keep
    assert "/enable" in keep
    monthly = (WF / "cost-monthly.yml").read_text(encoding="utf-8")
    assert f"peter-evans/create-pull-request@{CPR_SHA}" in monthly
    assert "create-pull-request@v8" not in monthly
    assert "cost-trend" in monthly
    assert "0 9 * * 1" in monthly


def test_issue_fix_is_draft():
    text = (WF / "cost-issue-fix.yml").read_text(encoding="utf-8")
    assert "good first issue" in text
    assert "draft: true" in text
    assert f"peter-evans/create-pull-request@{CPR_SHA}" in text
    assert "create-pull-request@v8" not in text


def test_pyproject_does_not_pip_install_steampipe_or_trivy069():
    text = (ROOT / "cost" / "pyproject.toml").read_text(encoding="utf-8")
    assert "steampipe==" not in text
    assert "trivy==0.69" not in text
    assert "c7n==0.9.45" in text
