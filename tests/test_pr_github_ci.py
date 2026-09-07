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


def test_auto_approve_and_bare_codeql_are_optional() -> None:
    summary = summarize_ci_checks(
        [
            _check("test"),
            _check("sspm-ci"),
            _check("auto-approve", conclusion="failure"),
            _check("CodeQL", conclusion="failure"),
            _check("CodeQL (python)"),
            _check("executive-consensus", conclusion="failure"),
        ]
    )
    assert summary["fail"] is False
    assert summary["pass"] is True


def test_codeql_python_workflow_job_is_required() -> None:
    summary = summarize_ci_checks(
        [
            _check("test"),
            _check("CodeQL (python)", conclusion="failure"),
        ]
    )
    assert summary["fail"] is True


def test_draft_executive_does_not_reject_auto_approve_failure() -> None:
    ci = summarize_ci_checks(
        [
            _check("test"),
            _check("auto-approve", conclusion="failure"),
            _check("CodeQL", conclusion="failure"),
        ]
    )
    ex = pr_draft_executive(
        {
            "number": 76,
            "title": "SSPM",
            "body": "[auto-approved]",
            "draft": False,
            "additions": 80,
            "deletions": 10,
            "changed_files": 4,
            "ci": ci,
            "files": [{"path": "tests/test_sspm_architecture.py"}],
            "labels": [],
        }
    )
    assert ex["verdict"] != "REJECT"
    assert "CI checks failed" not in ex["structural_gaps"]
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


def test_dismiss_stale_change_requests_targets_bot_rejects(monkeypatch) -> None:
    from engine import pr_github

    calls: list[list[str]] = []

    def fake_json(args):
        assert args[0] == "api"
        return [
            {"id": 1, "state": "CHANGES_REQUESTED", "user": {"login": "github-actions[bot]"}},
            {"id": 2, "state": "COMMENTED", "user": {"login": "github-actions[bot]"}},
            {"id": 3, "state": "CHANGES_REQUESTED", "user": {"login": "alice"}},
            {"id": 4, "state": "CHANGES_REQUESTED", "user": {"login": "github-actions[bot]"}},
        ]

    def fake_run(args):
        calls.append(args)
        return "{}"

    monkeypatch.setattr(pr_github, "_gh_json", fake_json)
    monkeypatch.setattr(pr_github, "_gh_run", fake_run)
    result = pr_github.dismiss_stale_change_requests(76, "km-git/newrepo")
    assert result["action"] == "dismiss_stale_change_requests"
    assert [row["id"] for row in result["dismissed"]] == [1, 4]
    assert result["errors"] == []
    assert len(calls) == 2
    joined = " ".join(" ".join(c) for c in calls)
    assert "/reviews/1/dismissals" in joined
    assert "/reviews/4/dismissals" in joined
    assert "/reviews/3/dismissals" not in joined
