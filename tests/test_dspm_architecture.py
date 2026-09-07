"""DSPM architecture, safety gates, and prompt-integrity tests."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DSPM = ROOT / "dspm"

MODULES = (
    "audit",
    "discovery",
    "classification",
    "risk",
    "access",
    "exposure",
    "encryption_check",
    "shadow",
    "custom_types",
    "compliance",
    "ai_security",
    "remediation",
)

WORKFLOWS = (
    "dspm-ci.yml",
    "dspm-watch.yml",
    "dspm-auto-approve.yml",
    "dspm-rebase.yml",
    "dspm-monthly.yml",
    "dspm-keepalive.yml",
    "dspm-issue-fix.yml",
)


def test_twelve_modules_have_cli_service_models_readme() -> None:
    for name in MODULES:
        folder = DSPM / name
        for filename in ("cli.py", "service.py", "models.py", "README.md", "__init__.py"):
            assert (folder / filename).is_file(), f"missing {name}/{filename}"
        readme = (folder / "README.md").read_text(encoding="utf-8")
        assert len(readme.split()) <= 200


def test_loop_reuses_watch_and_sources() -> None:
    assert (DSPM / "loop" / "watch.py").is_file()
    assert (DSPM / "loop" / "sources.yaml").is_file()
    assert (ROOT / "scripts" / "watch.py").is_file()
    sources = (DSPM / "loop" / "sources.yaml").read_text(encoding="utf-8")
    for needle in (
        "r/cybersecurity",
        "data-privacy-stack/presidio",
        "prowler-cloud/prowler",
        "aquasecurity/trivy",
        "cloud-custodian/cloud-custodian",
        "cohesity/dataprotect-mock-cookies",
        "lobste.rs/t/security",
        "trackawesomelist.com",
        "pypi.org/rss/project",
    ):
        assert needle in sources


def test_dspm_ci_pip_audit_skips_unpublished_local_package() -> None:
    text = (ROOT / ".github" / "workflows" / "dspm-ci.yml").read_text(encoding="utf-8")
    assert "pip-audit --strict" not in text
    assert "--skip-editable" in text
    assert "continue-on-error: true" in text
    assert "pip-audit -r requirements.txt" not in text
    lint = (ROOT / ".github" / "workflows" / "lint-security.yml").read_text(encoding="utf-8")
    assert "--ignore-vuln PYSEC-2026-2447" in lint


def test_workflows_exist_and_sha_pin_actions() -> None:
    for name in WORKFLOWS:
        path = ROOT / ".github" / "workflows" / name
        text = path.read_text(encoding="utf-8")
        assert path.is_file()
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            assert "aquasecurity/trivy-action@" not in stripped, "use setup-trivy SHA, not trivy-action tags"
            assert "@v" not in stripped.split("#")[0], f"unpinned tag in {name}: {stripped}"
            token = stripped.split()[1]
            sha = token.split("@", 1)[1]
            assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha), sha


def test_trivy_malicious_versions_refused() -> None:
    from dspm.tools import ToolError, assert_trivy_allowed

    assert assert_trivy_allowed("0.71.2") == "0.71.2"
    assert assert_trivy_allowed("Version: 0.70.0") == "0.70.0"
    for bad in ("0.69.4", "v0.69.4", "0.69.5", "0.64.1"):
        try:
            assert_trivy_allowed(bad)
        except ToolError as exc:
            assert "CVE-2026-33634" in str(exc)
        else:
            raise AssertionError(f"should refuse {bad}")


def test_steampipe_never_imported_as_library() -> None:
    for path in DSPM.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("steampipe"), path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("steampipe"), path
    access = (DSPM / "access" / "service.py").read_text(encoding="utf-8")
    assert 'run_cli("steampipe"' in access or "run_cli('steampipe'" in access


def test_presidio_source_is_data_privacy_stack() -> None:
    from dspm.constants import PRESIDIO_SOURCE

    assert PRESIDIO_SOURCE == "data-privacy-stack/presidio"
    blob = "\n".join(
        p.read_text(encoding="utf-8") for p in [DSPM / "constants.py", DSPM / "classification" / "recognizers.py"]
    )
    assert "microsoft/presidio" not in blob or "not microsoft/presidio" in blob


def test_auto_approve_workflow_avoids_zizmor_high_findings() -> None:
    text = (ROOT / ".github" / "workflows" / "dspm-auto-approve.yml").read_text(encoding="utf-8")
    assert "pull_request_target" not in text
    assert "github.actor ==" not in text
    assert "github.event.pull_request.user.login" in text
    assert "head.repo.full_name" in text


def test_auto_approve_skips_humans_and_remediation_policies() -> None:
    from dspm.loop.auto_approve import should_auto_approve

    assert should_auto_approve(actor="alice")["approve"] is False
    assert should_auto_approve(actor="dependabot[bot]")["approve"] is True
    blocked = should_auto_approve(
        actor="dependabot[bot]",
        changed_files=["dspm/remediation/policies/c7n-revoke-public-s3.yaml"],
    )
    assert blocked["approve"] is False


def test_issue_fix_requires_good_first_issue_and_mechanical_body() -> None:
    from dspm.loop.issue_fix import is_mechanical_issue

    body = "Expected behavior\nCurrent behavior\nSteps to reproduce\nFix the typo in README"
    assert is_mechanical_issue("typo in docs", body, ["good first issue"])["eligible"] is True
    semantic = "Expected behavior\nCurrent behavior\nSteps to reproduce\nChange the risk weights using new ML"
    assert is_mechanical_issue("rewrite risk formula", semantic, ["good first issue"])["eligible"] is False
    assert is_mechanical_issue("typo in docs", body, ["bug"])["eligible"] is False


def test_four_custodian_policies_present() -> None:
    names = {p.name for p in (DSPM / "remediation" / "policies").glob("c7n-*.yaml")}
    assert names == {
        "c7n-revoke-public-s3.yaml",
        "c7n-encrypt-unencrypted-rds.yaml",
        "c7n-mask-pii-laced-s3.yaml",
        "c7n-alert-on-shadow-bucket.yaml",
    }


def test_keepalive_does_not_use_disabled_marketplace_action() -> None:
    text = (ROOT / ".github" / "workflows" / "dspm-keepalive.yml").read_text(encoding="utf-8")
    assert "uses: gautamkrishnar/keepalive-workflow" not in text
    assert "state/keepalive.txt" in text


def test_custom_type_registry_ships_au_and_nhs() -> None:
    from dspm.custom_types.service import load_registry

    names = {item.name for item in load_registry().types}
    assert names == {"au_tfn", "au_abn", "nhs_number"}


def test_dspm_rebase_does_not_checkout_untrusted_head() -> None:
    text = (ROOT / ".github" / "workflows" / "dspm-rebase.yml").read_text(encoding="utf-8")
    assert "github.event.pull_request.head.ref" not in text
    assert "git push --force" not in text
    assert "uses: actions/checkout" not in text
    assert "@dependabot rebase" in text
