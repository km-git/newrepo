"""Integrity checks for cost GitHub workflows and Trivy pin."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"

TRIVY_SHA = "57a97c7e7821a5776cebc9bb87c984fa69cba8f1"


def test_cost_ci_has_merge_group_and_trivy_pin():
    text = (WF / "cost-ci.yml").read_text(encoding="utf-8")
    assert "merge_group" in text
    assert f"aquasecurity/trivy-action@{TRIVY_SHA}" in text
    assert "v0.71.2" in text
    assert "v0.69.4" in text  # mentioned as never
    assert "@latest" not in text.split("trivy-action")[0] or "trivy-action@57a97c7e" in text


def test_auto_approve_filters_actors_and_remediation():
    text = (WF / "cost-auto-approve.yml").read_text(encoding="utf-8")
    assert "pull_request_target" in text
    assert "dependabot[bot]" in text
    assert "[auto-approved]" in text
    assert "hmarr/auto-approve-action@v4" in text
    assert "cost/remediation/" in text
    assert "merge_group" in text


def test_watch_cron_is_monday_aest():
    text = (WF / "cost-watch.yml").read_text(encoding="utf-8")
    assert "0 9 * * 1" in text
    assert "Australia/Sydney" in text
    assert "peter-evans/create-pull-request@v8" in text


def test_keepalive_and_monthly():
    keep = (WF / "cost-keepalive.yml").read_text(encoding="utf-8")
    assert "gautamkrishnar/keepalive-workflow@v2" in keep
    monthly = (WF / "cost-monthly.yml").read_text(encoding="utf-8")
    assert "cost-trend" in monthly
    assert "0 9 * * 1" in monthly


def test_issue_fix_is_draft():
    text = (WF / "cost-issue-fix.yml").read_text(encoding="utf-8")
    assert "good first issue" in text
    assert "draft: true" in text


def test_pyproject_does_not_pip_install_steampipe_or_trivy069():
    text = (ROOT / "cost" / "pyproject.toml").read_text(encoding="utf-8")
    assert "steampipe==" not in text
    assert "trivy==0.69" not in text
    assert "c7n==0.9.45" in text
