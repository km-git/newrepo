"""SSPM report writer: SHA-256, disclaimer, forbidden words."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from sspm.disclaimers.service import show
from sspm.report_writer.service import generate, strip_forbidden


def test_strip_forbidden_words() -> None:
    cleaned, hits = strip_forbidden("This is certified and guaranteed to be secure.")
    assert "certified" in hits
    assert "guaranteed" in hits
    assert "secure" in hits
    lower = cleaned.lower()
    assert "certified" not in lower
    assert "guaranteed" not in lower
    assert "secure" not in lower


def test_generate_report_has_disclaimer_and_hash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    dest = Path("report.md")
    result = generate(tenant="m365", tenant_name="demo-customer", output=dest)
    text = Path(result.markdown).read_text(encoding="utf-8")
    assert text.startswith("# Configuration & Inventory Report")
    assert "Liability disclaimer" in text
    assert show().text.strip() in text
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == result.sha256
    assert Path(result.json_path).is_file()
    assert Path(result.html or "").is_file()
    for word in ("compliance", "attestation", "certified", "guaranteed"):
        assert f" {word} " not in text.lower()
    assert result.forbidden_hits == []
    assert "security assessment" in text.lower()  # the negation sentence is allowed
    json_text = Path(result.json_path).read_text(encoding="utf-8")
    assert "demo-customer" in json_text or "Contoso" in json_text


def test_generate_rejects_path_escape(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="working directory"):
        generate(tenant="m365", output=Path("/etc/sspm-report.md"))
    with pytest.raises(ValueError, match="unsupported report filename"):
        generate(tenant="m365", output=Path("evil.md"))


def test_email_redact_is_bounded() -> None:
    from sspm.redact import looks_like_email, scrub_text

    assert looks_like_email("ops@example.com")
    assert not looks_like_email("%" * 4000)
    assert "[REDACTED-EMAIL]" in scrub_text("write to ops@example.com please")
