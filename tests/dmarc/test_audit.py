from __future__ import annotations

from pathlib import Path

from dmarc.audit.service import run_inventory
from dmarc.cli import main
from dmarc.store import connect, fetch_all


def test_inventory_creates_tables_and_json(tmp_path: Path) -> None:
    payload = run_inventory(tmp_path)
    assert payload["path"].endswith("dmarc-inventory.json")
    assert (tmp_path / "dmarc-inventory.json").exists()
    names = {t["name"] for t in payload["tools"]}
    assert "dnspython" in names
    assert "parsedmarc" in names
    conn = connect(tmp_path)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    for table in (
        "findings_dns",
        "findings_spf",
        "findings_dkim",
        "findings_dmarc",
        "findings_forensic",
        "findings_inbox",
    ):
        assert table in tables
        assert fetch_all(table, root=tmp_path) == []


def test_cli_audit_inventory(tmp_path: Path) -> None:
    assert main(["audit", "inventory", "--output-dir", str(tmp_path)]) == 0
