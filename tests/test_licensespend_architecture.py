"""LicenseSpend architecture, safety gates, and prompt-integrity tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "licensespend"

MODULES = (
    "audit",
    "m365",
    "slack",
    "github",
    "usage",
    "shadow",
    "renewals",
    "report",
)

WORKFLOWS = (
    "licensespend-ci.yml",
    "licensespend-watch.yml",
    "licensespend-auto-approve.yml",
    "licensespend-rebase.yml",
    "licensespend-monthly.yml",
    "licensespend-keepalive.yml",
    "licensespend-issue-fix.yml",
)


def test_eight_modules_have_cli_service_models_readme() -> None:
    for name in MODULES:
        folder = PKG / name
        for filename in ("cli.py", "service.py", "models.py", "README.md", "__init__.py"):
            assert (folder / filename).is_file(), f"missing {name}/{filename}"
        readme = (folder / "README.md").read_text(encoding="utf-8")
        assert len(readme.split()) <= 200


def test_loop_reuses_forum_watcher_and_sources() -> None:
    assert (PKG / "loop" / "sources.yaml").is_file()
    assert (ROOT / "forum-watcher" / "scripts" / "watch.py").is_file()
    sources = (ROOT / "forum-watcher" / "sources.yaml").read_text(encoding="utf-8")
    for needle in (
        "r/msp",
        "r/PowerShell",
        "msgraph-sdk-python",
        "python-slack-sdk",
        "PyGithub/PyGithub",
        "saas%20sprawl",
        "unused%20licenses",
        "slack%20billed%20seats",
    ):
        assert needle in sources, needle
    block = (ROOT / "forum-watcher" / "blocklist.yaml").read_text(encoding="utf-8").lower()
    for vendor in ("zylo", "productiv", "torii"):
        assert vendor in block


def test_workflows_exist_and_sha_pin_actions() -> None:
    for name in WORKFLOWS:
        path = ROOT / ".github" / "workflows" / name
        text = path.read_text(encoding="utf-8")
        assert path.is_file()
        if name == "licensespend-ci.yml":
            assert "LICENSESPEND_INCLUDE_EMAIL" in text
            assert "LICENSESPEND_APPLY" in text
        if name == "licensespend-watch.yml":
            assert "Australia/Sydney" in text
        if name == "licensespend-keepalive.yml":
            assert "licensespend/state/keepalive.txt" in text
            assert "uses: gautamkrishnar/" not in text
        if name == "licensespend-auto-approve.yml":
            assert "dependabot[bot]" in text
            assert "hmarr/auto-approve-action@" in text
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            assert "@v" not in stripped.split("#")[0], f"unpinned tag in {name}: {stripped}"
            token = stripped.split()[1]
            sha = token.split("@", 1)[1]
            assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha), sha


def test_cursor_rule_and_pricebook_and_no_minio() -> None:
    rule = (ROOT / ".cursor" / "rules" / "licensespend-build.mdc").read_text(encoding="utf-8")
    assert "8-module" in rule or "8 modules" in rule
    assert "LICENSESPEND_APPLY" in rule
    pricebook = (PKG / "usage" / "pricebook.yaml").read_text(encoding="utf-8")
    assert "monthly_aud" in pricebook
    assert "m365-e3" in pricebook
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "5435:5432" in compose
    assert "minio" not in compose.lower()
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "licensespend-all" in makefile
    assert (PKG / "state" / "keepalive.txt").is_file()
    assert (PKG / "allow-reclaim.txt").is_file()


def test_fixtures_golden_shape() -> None:
    import json

    users = json.loads((ROOT / "examples" / "m365" / "users.json").read_text(encoding="utf-8"))
    assert len(users["users"]) == 12
    assert all("user_id" in row and "sku" in row and "last_active" in row for row in users["users"])
    slack = json.loads((ROOT / "examples" / "slack" / "users_list.json").read_text(encoding="utf-8"))
    guests = [
        m
        for m in slack["members"]
        if m.get("is_restricted") or m.get("is_ultra_restricted") or m.get("role") == "guest"
    ]
    assert len(guests) == 2
    github = json.loads((ROOT / "examples" / "github" / "members.json").read_text(encoding="utf-8"))
    outside = [m for m in github["members"] if m.get("role") == "outside_collaborator"]
    assert len(outside) == 1
