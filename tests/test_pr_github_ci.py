"""Advisory GitHub checks must not REJECT a PR that passed required CI."""

from __future__ import annotations

from engine.pr_executive import pr_draft_executive
from engine.pr_github import summarize_ci_checks


def _check(name: str, *, conclusion: str | None = "success", status: str = "completed") -> dict:
    return {"name": name, "conclusion": conclusion, "status": status}


def test_pip_audit_and_bugbot_are_optional() -> None:
    summary = summarize_ci_checks(
        [
            _check("test"),
            _check("ruff (tape-to-cloud + monetization)"),
            _check("pip-audit (requirements.txt)", conclusion="failure"),
            _check("Cursor Bugbot", conclusion="neutral"),
            _check("executive-consensus", conclusion="failure"),
        ]
    )
    assert summary["fail"] is False
    assert summary["pending"] is False
    assert summary["pass"] is True


def test_required_test_failure_still_fails() -> None:
    summary = summarize_ci_checks(
        [
            _check("test", conclusion="failure"),
            _check("pip-audit (requirements.txt)", conclusion="failure"),
        ]
    )
    assert summary["fail"] is True
    assert summary["pass"] is False


def test_pending_required_check_is_pending_not_fail() -> None:
    summary = summarize_ci_checks(
        [
            _check("test", conclusion=None, status="in_progress"),
            _check("pip-audit (requirements.txt)", conclusion="failure"),
        ]
    )
    assert summary["fail"] is False
    assert summary["pending"] is True
    assert summary["pass"] is False


def test_draft_executive_does_not_reject_advisory_ci_failures() -> None:
    ci = summarize_ci_checks(
        [
            _check("test"),
            _check("pip-audit (requirements.txt)", conclusion="failure"),
            _check("Cursor Bugbot", conclusion="neutral"),
        ]
    )
    ex = pr_draft_executive(
        {
            "number": 59,
            "title": "Bugbot replacement",
            "body": "Ruff + PR-Agent",
            "draft": False,
            "additions": 80,
            "deletions": 10,
            "changed_files": 4,
            "ci": ci,
            "files": [{"path": "tests/test_bugbot_replacement.py"}],
            "labels": [],
        }
    )
    assert ex["verdict"] != "REJECT"
    assert "CI checks failed" not in ex["structural_gaps"]
