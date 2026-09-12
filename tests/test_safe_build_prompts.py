"""Guardrails for the four paste-ready Composer prompt files."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "4-safe-builds-prompts"

FILES = {
    "01-SSPM-CURSOR-PROMPT.md": {
        "needles": ["Mondoo cnspec", "12-module", "## 0. Read first", "sspm/"],
        "forbidden_start": ("```", "## "),
    },
    "02-CLOUD-COST-CONFIG-CURSOR-PROMPT.md": {
        "needles": ["Prowler", "Steampipe", "Cloud Custodian", "10-module", "costreview/"],
        "forbidden_start": ("```", "## "),
    },
    "03-SAAS-LICENSE-CURSOR-PROMPT.md": {
        "needles": ["Microsoft Graph", "Slack SDK", "PyGithub", "8-module", "licensespend/"],
        "forbidden_start": ("```", "## "),
    },
    "04-DMARC-DELIVERABILITY-CURSOR-PROMPT.md": {
        "needles": ["parsedmarc", "dnspython", "9-module", "dmarcdeliv/"],
        "forbidden_start": ("```", "## "),
    },
}


@pytest.fixture(scope="module")
def prompt_dir() -> Path:
    assert PROMPT_DIR.is_dir(), f"missing {PROMPT_DIR}"
    return PROMPT_DIR


def test_all_five_files_present(prompt_dir: Path) -> None:
    names = {p.name for p in prompt_dir.glob("*.md")}
    expected = set(FILES) | {"ALL-4-BUILDS-MASTER.md"}
    assert expected <= names, f"missing {expected - names}"


@pytest.mark.parametrize("filename", sorted(FILES))
def test_standalone_prompt_is_raw_body(prompt_dir: Path, filename: str) -> None:
    spec = FILES[filename]
    text = (prompt_dir / filename).read_text(encoding="utf-8")
    assert text.strip(), filename
    assert text.startswith("You are "), f"{filename} must start with You are"
    for prefix in spec["forbidden_start"]:
        assert not text.startswith(prefix), f"{filename} must not start with {prefix!r}"
    stripped = text.rstrip()
    assert not stripped.endswith("```"), f"{filename} must not close with an outer fence"
    for needle in spec["needles"]:
        assert needle in text, f"{filename} missing {needle!r}"
    assert "gautamkrishnar/keepalive-workflow" in text
    assert "CVE-2026-33634" in text
    assert "Australia/Sydney" in text
    assert "$0" in text


def test_master_has_framing_and_twenty_eight_references(prompt_dir: Path) -> None:
    text = (prompt_dir / "ALL-4-BUILDS-MASTER.md").read_text(encoding="utf-8")
    assert text.startswith("# Four Safe Builds")
    for n in range(1, 29):
        assert f"[{n}]" in text, f"missing reference [{n}]"
    for filename in FILES:
        assert filename in text
