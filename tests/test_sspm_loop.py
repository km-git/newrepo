"""SSPM Discover loop, classifier, issue auto-fix."""

from __future__ import annotations

from pathlib import Path

from sspm.loop.classify import SSPM_CONTEXT, classify_item
from sspm.loop.issue_fix import is_mechanical_issue
from sspm.loop.monthly import generate_monthly
from sspm.loop.watch import url_hash, watch


def test_url_hash_sha256() -> None:
    digest = url_hash("https://github.com/mondoohq/cnspec/releases/tag/v13.37.0")
    assert len(digest) == 64
    assert digest == url_hash("https://github.com/mondoohq/cnspec/releases/tag/v13.37.0")


def test_classifier_locks_module_and_discovers() -> None:
    item = {
        "title": "Mondoo cnspec 13.37.0 SSPM policy pack for Microsoft 365",
        "summary": "cnspec scan microsoft365 CIS-M365 google workspace okta",
        "source": "cnspec-releases",
        "module_hint": "sspm/m365_discovery",
    }
    result = classify_item(item)
    assert result["verdict"] == "discover"
    assert result["module"] == "m365_discovery"
    assert result["context_attached"] is True
    assert "SSPM" in SSPM_CONTEXT


def test_watch_offline_writes_queue(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = watch(mode="offline", fetch=False)
    assert payload["discover"] >= 1
    assert Path("state/discover_queue.json").is_file()
    assert Path("state/seen.json").is_file()


def test_monthly_rollup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    watch(mode="offline")
    result = generate_monthly(out_dir=tmp_path / "monthly")
    text = Path(result["path"]).read_text(encoding="utf-8")
    assert "attestation" not in text.lower() or "not an attestation" in text.lower()
    assert result["month"]


def test_issue_fix_mechanical_gate() -> None:
    body = """
Expected behavior: README typo fixed
Current behavior: typo in fixture docs
Steps to reproduce: open README
"""
    ok = is_mechanical_issue("typo in README", body, ["good first issue"])
    assert ok["eligible"] is True
    blocked = is_mechanical_issue("rewrite disclaimers", body + " change sspm/disclaimers", ["good first issue"])
    assert blocked["eligible"] is False
    missing = is_mechanical_issue("typo", "no headings", ["good first issue"])
    assert missing["eligible"] is False
