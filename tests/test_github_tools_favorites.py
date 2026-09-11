"""GitHub-native scanner favorites replace Cursor Bugbot (usage-cap skip)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUGBOT_FREE = ROOT / ".github" / "workflows" / "bugbot-free.yml"
LINT_SECURITY = ROOT / ".github" / "workflows" / "lint-security.yml"
ZIZMOR = ROOT / "zizmor.yml"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"

# SHA pins copied from the inventory / main Bugbot-free stack.
CODEQL_SHA = "cdf488f595d80d6e07e03d4674febd5ab45fa938"
GITLEAKS_SHA = "e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e"
OSV_SHA = "6e4298ebc4db23e847df9b2e2de2939d6f066c67"
TRUFFLEHOG_SHA = "363923b901c911a9164f50b6c423f47c15372b1c"
REVIEWDOG_SHA = "d8a7baabd7f3e8544ee4dbde3ee41d0011c3a93f"


def test_bugbot_free_workflow_uses_github_native_favorites() -> None:
    text = BUGBOT_FREE.read_text(encoding="utf-8")
    assert "Do not retry Cursor Bugbot" in text
    assert "github/codeql-action/init@" + CODEQL_SHA in text
    assert "github/codeql-action/analyze@" + CODEQL_SHA in text
    assert "languages: ${{ matrix.language }}" in text
    assert "python" in text and "actions" in text
    assert "semgrep scan" in text
    assert "--config p/security-audit" in text
    assert "reviewdog/action-setup@" + REVIEWDOG_SHA in text
    assert "persist-credentials: false" in text
    assert "cursor[bot]" not in text.lower() or "Do not retry Cursor Bugbot" in text


def test_lint_security_covers_secret_supply_chain_and_workflow_favorites() -> None:
    text = LINT_SECURITY.read_text(encoding="utf-8")
    for needle in (
        "gitleaks/gitleaks-action@" + GITLEAKS_SHA,
        "google/osv-scanner-action/osv-scanner-action@" + OSV_SHA,
        "trufflesecurity/trufflehog@" + TRUFFLEHOG_SHA,
        "github/codeql-action/upload-sarif@" + CODEQL_SHA,
        "zizmor --config zizmor.yml",
        "actionlint_1.7.12_linux_amd64.tar.gz",
        "persist-credentials: false",
        "--only-verified",
    ):
        assert needle in text, f"missing {needle}"
    assert "uses: reviewdog/action-setup" not in text  # CVE-2025-30154; reviewdog lives in bugbot-free.yml


def test_dependabot_and_zizmor_config_present() -> None:
    dep = DEPENDABOT.read_text(encoding="utf-8")
    assert "package-ecosystem: pip" in dep
    assert "package-ecosystem: github-actions" in dep
    ziz = ZIZMOR.read_text(encoding="utf-8")
    assert "unpinned-uses" in ziz
    assert "ref-pin" in ziz


def test_advisory_github_scanners_are_optional_for_pr_consensus() -> None:
    from engine.pr_github import _is_required_ci_check

    assert _is_required_ci_check({"name": "pip-audit (requirements.txt)"}) is False
    assert _is_required_ci_check({"name": "Cursor Bugbot"}) is False
    assert _is_required_ci_check({"name": "Semgrep CE + reviewdog"}) is False
    assert _is_required_ci_check({"name": "CodeQL"}) is False
    assert _is_required_ci_check({"name": "test"}) is True
    assert _is_required_ci_check({"name": "CodeQL (python)"}) is True
    assert _is_required_ci_check({"name": "gitleaks (secrets)"}) is True
    assert _is_required_ci_check({"name": "osv-scanner (requirements)"}) is True
    assert _is_required_ci_check({"name": "zizmor (workflows)"}) is True
    assert _is_required_ci_check({"name": "trufflehog (verified secrets)"}) is True
