"""SSPM package architecture contracts."""

from __future__ import annotations

from pathlib import Path

from sspm import FORBIDDEN_REPORT_WORDS, MODULES, TENANT_TYPES

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "sspm"


def test_twelve_modules_present() -> None:
    assert len(MODULES) == 12
    for name in MODULES:
        folder = PKG / name
        for required in ("__init__.py", "cli.py", "service.py", "models.py", "README.md"):
            assert (folder / required).is_file(), f"missing {name}/{required}"
        readme = (folder / "README.md").read_text(encoding="utf-8")
        assert len(readme.split()) <= 200


def test_tenant_types() -> None:
    assert TENANT_TYPES == ("m365", "gws", "github", "slack", "okta")
    for kind in TENANT_TYPES:
        assert (PKG / "fixtures" / f"{kind}.json").is_file()
        assert (PKG / "baselines" / f"{kind}.json").is_file()


def test_forbidden_report_words() -> None:
    assert "compliance" in FORBIDDEN_REPORT_WORDS
    assert "attestation" in FORBIDDEN_REPORT_WORDS


def test_schema_tables() -> None:
    schema = (PKG / "db" / "schema.sql").read_text(encoding="utf-8")
    for table in (
        "findings_tenants",
        "findings_settings",
        "findings_oauth",
        "findings_drift",
        "findings_compliance",
        "tenants",
    ):
        assert table in schema


def test_workflows_exist() -> None:
    wf = ROOT / ".github" / "workflows"
    for name in (
        "sspm-ci.yml",
        "sspm-auto-approve.yml",
        "sspm-rebase.yml",
        "sspm-monthly.yml",
        "sspm-keepalive.yml",
        "sspm-watch.yml",
        "sspm-issue-fix.yml",
    ):
        assert (wf / name).is_file()
    ci = (wf / "sspm-ci.yml").read_text(encoding="utf-8")
    assert "merge_group" in ci
    assert "pip-audit --strict" in ci
    assert "sspm/requirements-ci.txt" in ci
    approve = (wf / "sspm-auto-approve.yml").read_text(encoding="utf-8")
    assert "pull_request_target" not in approve
    assert "pull_request:" in approve
    assert "github.event.pull_request.user.login" in approve
    assert "dependabot[bot]" in approve
    assert "[auto-approved]" in approve
    assert "hmarr/auto-approve-action" in approve
    watch = (wf / "sspm-watch.yml").read_text(encoding="utf-8")
    assert "Australia/Sydney" in watch
    rebase = (wf / "sspm-rebase.yml").read_text(encoding="utf-8")
    assert "actions/checkout" not in rebase
    assert "gh pr checkout" not in rebase
    assert "update-branch" in rebase
