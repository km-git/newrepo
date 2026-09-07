"""CLI smoke: JSON default and --human table."""

from __future__ import annotations

import json
from pathlib import Path

from sspm.cli import main


def test_cli_audit_json(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SSPM_DB", str(tmp_path / "sspm.sqlite"))
    assert main(["audit", "inventory"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["product"] == "sspm"
    assert payload["tool_count"] >= 10


def test_cli_human_and_report(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SSPM_DB", str(tmp_path / "sspm.sqlite"))
    assert main(["--human", "disclaimers", "show", "--name", "disclaimer_au"]) == 0
    out = capsys.readouterr().out
    assert "disclaimer_au" in out
    assert main(["report", "generate", "--tenant", "github", "--output", str(tmp_path / "g.md")]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert Path(payload["markdown"]).is_file()
    assert payload["sha256"]
