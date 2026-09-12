"""LicenseSpend unused-seat math, hashing, reclaim gates (skipped if extras missing)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("duckdb")
pytest.importorskip("typer")
pytest.importorskip("jinja2")

from licensespend.constants import EXAMPLES
from licensespend.privacy import contains_raw_email, hash_email
from licensespend.reclaim import ReclaimDenied, reclaim_seats
from licensespend.report.service import build, verify_watermark
from licensespend.usage.service import unused_seats

ROOT = Path(__file__).resolve().parents[1]


def test_unused_seat_math_and_hashed_emails() -> None:
    report = unused_seats(fixture_root=EXAMPLES, idle_days=90, as_of=date(2026, 9, 7))
    assert len([r for r in report.rows if r.sku == "m365-e3"]) == 3
    assert report.reclaim_monthly_aud == 127.0
    assert all(r.email is None for r in report.rows)
    digest = hash_email("alex@contoso.example", salt="licensespend-dev")
    assert len(digest) == 64
    assert digest != "alex@contoso.example"


def test_reclaim_requires_dual_gates(tmp_path: Path, monkeypatch) -> None:
    allow = tmp_path / "allow-reclaim.txt"
    allow.write_text("u-001\n", encoding="utf-8")
    draft = reclaim_seats(["u-001"], apply=False, allow_path=allow)
    assert draft["revoked"] is False
    monkeypatch.delenv("LICENSESPEND_APPLY", raising=False)
    with pytest.raises(ReclaimDenied):
        reclaim_seats(["u-001"], apply=True, allow_path=allow)
    monkeypatch.setenv("LICENSESPEND_APPLY", "1")
    with pytest.raises(ReclaimDenied):
        reclaim_seats(["u-999"], apply=True, allow_path=allow)
    recorded = reclaim_seats(["u-001"], apply=True, allow_path=allow)
    assert recorded["revoked"] is False
    assert recorded["action"] == "recorded-intent"


def test_report_build_watermark(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LICENSESPEND_INCLUDE_EMAIL", "0")
    files = build(client="fixture", out_dir=tmp_path, fixture_root=EXAMPLES, as_of=date(2026, 9, 7))
    assert verify_watermark(Path(files.json_path))
    for path in (files.json_path, files.markdown_path, files.html_path):
        text = Path(path).read_text(encoding="utf-8")
        assert not contains_raw_email(text)
    assert files.reclaim_monthly_aud == 127.0
