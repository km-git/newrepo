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
GITLEAKS_SHA = "ff98106e4c7b2bc287b24eaf42907196329070c7"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*uses:\s+(\S+)", re.MULTILINE)


def test_guide_describes_the_five_minute_stack() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "Ruff" in text
    assert "PR-Agent" in text
    assert "CodeRabbit" in text
    assert "gitleaks" in text
    assert "Bandit" in text or "`S`" in text


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


def test_gitleaks_action_is_sha_pinned() -> None:
    text = LINT_SECURITY.read_text(encoding="utf-8")
    assert f"gitleaks/gitleaks-action@{GITLEAKS_SHA}" in text
    assert "gitleaks/gitleaks-action@v2" not in text
    assert "gitleaks/gitleaks-action@main" not in text
    assert "--ignore-vuln PYSEC-2026-2447" in text


def test_ruff_passes_on_replacement_paths() -> None:
    ruff = ROOT / ".venv" / "bin" / "ruff"
    binary = str(ruff) if ruff.exists() else shutil.which("ruff")
    if not binary:
        pytest.skip("ruff is not installed")
    paths = [
        "tape_to_cloud/",
        "engine/monetization_strategy.py",
        "tests/test_monetization_strategy.py",
        "tests/test_tape_to_cloud_monetize.py",
        "tests/test_bugbot_replacement.py",
    ]
    subprocess.run([binary, "check", "--config", str(RUFF_TOML), *paths], check=True, cwd=ROOT)
    subprocess.run([binary, "format", "--check", *paths], check=True, cwd=ROOT)
