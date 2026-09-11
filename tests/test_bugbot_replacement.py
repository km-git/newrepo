"""Integrity checks for the Ruff + PR-Agent Bugbot replacement."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUFF_TOML = ROOT / "ruff.toml"
PRECOMMIT = ROOT / ".pre-commit-config.yaml"
PR_AGENT = ROOT / ".github" / "workflows" / "pr-agent.yml"
LINT_SECURITY = ROOT / ".github" / "workflows" / "lint-security.yml"
GUIDE = ROOT / "mavis-deep-research" / "20260907_bugbot_replacement" / "final_turn_001.md"

RUFF_SELECT = ("E", "F", "W", "I", "UP", "B", "SIM", "RUF", "S")
PR_AGENT_SHA = "f3b385ea2927247ddcff2fe252472380b9c8f5fc"
GITLEAKS_SHA = "e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e"
CODEQL_SHA = "cdf488f595d80d6e07e03d4674febd5ab45fa938"
REVIEWDOG_SHA = "d8a7baabd7f3e8544ee4dbde3ee41d0011c3a93f"
SCORECARD_SHA = "2d1146689b8cda280b9bc96326124645441f03bc"
DEP_REVIEW_SHA = "3c4e3dcb1aa7874d2c16be7d79418e9b7efd6261"
CHECKOUT_SHA = "08c6903cd8c0fde910a37f88322edcfb5dd907a8"
SETUP_PYTHON_SHA = "e797f83bcb11b83ae66e0230d6156d7c80228e7c"
OSV_SHA = "6e4298ebc4db23e847df9b2e2de2939d6f066c67"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*uses:\s+(\S+)", re.MULTILINE)
BUGBOT_FREE = ROOT / ".github" / "workflows" / "bugbot-free.yml"
SCORECARD = ROOT / ".github" / "workflows" / "scorecard.yml"
DEP_REVIEW = ROOT / ".github" / "workflows" / "dependency-review.yml"
RENOVATE = ROOT / "renovate.json"


def test_guide_describes_the_five_minute_stack() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "Ruff" in text
    assert "PR-Agent" in text
    assert "CodeRabbit" in text
    assert "CodeQL" in text
    assert "Semgrep" in text
    assert "reviewdog" in text


def test_ruff_toml_selects_bugbot_replacement_rules() -> None:
    text = RUFF_TOML.read_text(encoding="utf-8")
    for code in RUFF_SELECT:
        assert f'"{code}"' in text, code
    assert "S" in text


def test_pre_commit_uses_current_ruff_not_guide_pin() -> None:
    text = PRECOMMIT.read_text(encoding="utf-8")
    assert "astral-sh/ruff-pre-commit" in text
    assert "id: ruff" in text
    assert "id: ruff-format" in text
    assert re.search(r"^\s+rev:\s+v0\.6\.9\s*$", text, re.MULTILINE) is None
    assert re.search(r"^\s+rev:\s+v0\.9\.\d+\s*$", text, re.MULTILINE)
    assert "E,F,W,I,UP,B,SIM,RUF,S" in text
    assert "--fix" in text


def test_pr_agent_workflow_is_sha_pinned_and_skips_without_key() -> None:
    text = PR_AGENT.read_text(encoding="utf-8")
    assert PR_AGENT.is_file()
    assert f"the-pr-agent/pr-agent@{PR_AGENT_SHA}" in text
    assert "v0.45.0" in text
    assert "OPENAI_KEY" in text
    assert "github_action_config.auto_review" in text
    assert "github_action_config.auto_describe" in text
    assert "github_action_config.auto_improve" in text
    assert "gpt-4o-mini" in text
    assert "present=true" in text
    assert "CodeRabbit" in text
    assert "pull_request_target" not in text
    assert "github.event.issue.pull_request" in text
    for uses in USES_RE.findall(text):
        assert not uses.endswith("@main"), uses
        ref = uses.split("@", 1)[1].split("#", 1)[0]
        assert SHA_RE.fullmatch(ref), uses


def test_no_compromised_reviewdog_action_setup_tag() -> None:
    """CVE-2025-30154 hit the mutable @v1 tag. SHA-pinned action-setup is allowed."""
    workflows = ROOT / ".github" / "workflows"
    for path in workflows.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "uses: reviewdog/action-setup@v1" not in text, path.name
        assert "uses: reviewdog/action-setup@main" not in text, path.name
        for uses in USES_RE.findall(text):
            if not uses.startswith("reviewdog/action-setup@"):
                continue
            ref = uses.split("@", 1)[1].split("#", 1)[0]
            assert SHA_RE.fullmatch(ref), uses
            assert ref == REVIEWDOG_SHA, uses


def test_codeql_and_trufflehog_are_sha_pinned() -> None:
    assert not (ROOT / ".github" / "workflows" / "codeql.yml").exists()
    bugbot = BUGBOT_FREE.read_text(encoding="utf-8")
    assert f"github/codeql-action/init@{CODEQL_SHA}" in bugbot
    assert f"github/codeql-action/analyze@{CODEQL_SHA}" in bugbot
    lint = LINT_SECURITY.read_text(encoding="utf-8")
    assert "trufflesecurity/trufflehog@363923b901c911a9164f50b6c423f47c15372b1c" in lint
    assert f"github/codeql-action/upload-sarif@{CODEQL_SHA}" in lint
    assert f"google/osv-scanner-action/osv-scanner-action@{OSV_SHA}" in lint
    assert "osv-scanner-action@v2" not in lint
    for uses in USES_RE.findall(bugbot + "\n" + lint):
        ref = uses.split("@", 1)[1].split("#", 1)[0]
        if "/" not in uses:
            continue
        if uses.startswith(("actions/checkout@", "actions/setup-python@")):
            assert SHA_RE.fullmatch(ref), uses
            continue
        if uses.startswith("actions/"):
            continue
        if uses.startswith(
            (
                "gitleaks/",
                "the-pr-agent/",
                "github/codeql-action/",
                "trufflesecurity/",
                "reviewdog/",
                "google/osv-scanner-action/",
            )
        ):
            assert SHA_RE.fullmatch(ref), uses
    text = LINT_SECURITY.read_text(encoding="utf-8")
    assert f"gitleaks/gitleaks-action@{GITLEAKS_SHA}" in text
    assert "gitleaks/gitleaks-action@v2" not in text
    assert "gitleaks/gitleaks-action@v3" not in text
    assert "gitleaks/gitleaks-action@main" not in text
    assert "--ignore-vuln PYSEC-2026-2447" in text
    allow = (ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
    assert "useDefault = true" in allow
    ignore = (ROOT / ".gitleaksignore").read_text(encoding="utf-8")
    assert "bb00f4049343f5e9b7636fb1f841a88af26daa1f:engine/tape_to_cloud_reports.py:generic-api-key:258" in ignore


def test_ruff_passes_on_replacement_paths() -> None:
    ruff = ROOT / ".venv" / "bin" / "ruff"
    binary = str(ruff) if ruff.exists() else shutil.which("ruff")
    if not binary:
        pytest.skip("ruff is not installed")
    paths = [
        "tape_to_cloud/",
        "engine/monetization_strategy.py",
        "engine/tape_to_cloud_hub.py",
        "engine/tape_to_cloud_reports.py",
        "tests/test_monetization_strategy.py",
        "tests/test_tape_to_cloud_monetize.py",
        "tests/test_tape_to_cloud_hub.py",
        "tests/test_tape_to_cloud_reports.py",
        "tests/test_tape_to_cloud_pipeline.py",
        "tests/test_bugbot_replacement.py",
        "dspm/",
        "tests/test_dspm_loop.py",
    ]
    subprocess.run([binary, "check", "--config", str(RUFF_TOML), *paths], check=True, cwd=ROOT)
    subprocess.run([binary, "format", "--check", *paths], check=True, cwd=ROOT)


def test_bugbot_free_workflow_is_sha_pinned_and_zero_key() -> None:
    text = BUGBOT_FREE.read_text(encoding="utf-8")
    assert "secrets.OPENAI_KEY" not in text
    assert "CURSOR" not in text
    assert f"github/codeql-action/init@{CODEQL_SHA}" in text
    assert f"github/codeql-action/analyze@{CODEQL_SHA}" in text
    assert f"github/codeql-action/upload-sarif@{CODEQL_SHA}" in text
    assert f"reviewdog/action-setup@{REVIEWDOG_SHA}" in text
    assert "semgrep" in text
    assert "p/security-audit" in text
    assert "pull_request_target" not in text
    assert f"actions/checkout@{CHECKOUT_SHA}" in text
    assert f"actions/setup-python@{SETUP_PYTHON_SHA}" in text
    for uses in USES_RE.findall(text):
        ref = uses.split("@", 1)[1].split("#", 1)[0]
        assert SHA_RE.fullmatch(ref), uses


def test_mend_socket_aikido_standins_are_free_and_sha_pinned() -> None:
    """Paid Mend/Socket/Aikido/Sourcery SaaS are not required; GitHub stand-ins are."""
    renovate = RENOVATE.read_text(encoding="utf-8")
    assert "config:best-practices" in renovate
    assert "github-actions" in renovate
    score = SCORECARD.read_text(encoding="utf-8")
    assert f"ossf/scorecard-action@{SCORECARD_SHA}" in score
    assert "v2.4.4" in score
    assert "pull_request_target" not in score
    dep = DEP_REVIEW.read_text(encoding="utf-8")
    assert f"actions/dependency-review-action@{DEP_REVIEW_SHA}" in dep
    assert "fail-on-severity: high" in dep
    combined = score + "\n" + dep
    assert f"actions/checkout@{CHECKOUT_SHA}" in combined
    for uses in USES_RE.findall(combined):
        ref = uses.split("@", 1)[1].split("#", 1)[0]
        assert SHA_RE.fullmatch(ref), uses
    workflows = ROOT / ".github" / "workflows"
    blob = "\n".join(p.read_text(encoding="utf-8") for p in workflows.glob("*.yml"))
    for paid in ("socket.dev", "aikido.dev", "sourcery.ai", "greptile.com", "codeant.ai"):
        assert paid not in blob
    assert "SENTRY_DSN" not in blob
    assert "LINEAR_API" not in blob
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "GitHub Security Advisories" in security
    assert "Do not open a public issue" in security
    script = ROOT / "scripts" / "run_free_scanners.sh"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "semgrep" in text
    assert "zizmor" in text
    assert "pip-audit" in text
    assert "PYSEC-2026-2447" in text
