from __future__ import annotations

from pathlib import Path

from dmarc.dmarc_ingest.service import ingest_fixtures
from dmarc.forbidden import contains_forbidden, sanitize_report_text
from dmarc.loop.monthly import write_monthly
from dmarc.loop.watch import heuristic_classify, url_hash
from dmarc.report_writer.service import TITLE, generate
from dmarc.webui import dispatch_dmarc, publish_static, render_explorer_html
from tests.dmarc.helpers import example_resolver


def test_report_title_disclaimer_and_banned_words(tmp_path: Path) -> None:
    ingest_fixtures(root=tmp_path)
    result = generate(
        "example.com.au",
        since="3650d",
        root=tmp_path,
        run_live=True,
        resolver=example_resolver(),
    )
    assert result["title"] == TITLE
    markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
    json_text = Path(result["json_path"]).read_text(encoding="utf-8")
    assert "Email Deliverability & Brand-Protection Review" in markdown
    assert "observational only" in markdown.lower() or "observational only" in json_text.lower()
    assert not contains_forbidden(markdown)
    dirty = "This compliance attestation is certified, secure, and guaranteed."
    assert contains_forbidden(dirty)
    clean = sanitize_report_text(dirty)
    assert not contains_forbidden(clean)


def test_webui_dispatch_and_static(tmp_path: Path, monkeypatch) -> None:
    ingest_fixtures(root=tmp_path)
    status, headers, body = dispatch_dmarc("GET", "/dmarc", output_root=tmp_path)  # type: ignore[misc]
    assert status == 200
    assert "text/html" in headers["Content-Type"]
    assert b"Brand-Protection" in body
    api, _, payload = dispatch_dmarc("GET", "/api/dmarc/status", output_root=tmp_path)  # type: ignore[misc]
    assert api == 200
    assert b"example.com.au" in payload or b"aggregate" in payload
    html = render_explorer_html(embedded=True)
    assert "Email Deliverability" in html
    monkeypatch.chdir(tmp_path)
    # publish_static writes reports/ relative to CWD
    (tmp_path / "reports").mkdir()
    from dmarc import webui as webui_mod

    monkeypatch.setattr(webui_mod, "STATIC_EXPLORER", tmp_path / "reports" / "dmarc_explorer.html")
    paths = publish_static(tmp_path)
    assert Path(paths["static"]).exists()


def test_watcher_hash_and_classify() -> None:
    digest = url_hash("https://github.com/domainaware/parsedmarc/releases/tag/8.6.4")
    assert len(digest) == 64
    item = {
        "title": "parsedmarc 8.6.4 how to pip install IMAP RUA",
        "summary": "dmarc_ingest aggregate report parser",
        "module_hint": "dmarc_ingest",
        "source": "parsedmarc releases",
    }
    result = heuristic_classify(item)
    assert result["verdict"] == "discover"
    assert result["module"] in {"dmarc_ingest", "aggregate_report"}


def test_monthly_rollup(tmp_path: Path) -> None:
    ingest_fixtures(root=tmp_path)
    monthly = tmp_path / "monthly"
    paths = write_monthly(root=tmp_path, monthly_dir=monthly)
    trend = Path(paths["trend"]).read_text(encoding="utf-8")
    assert "Deliverability trend" in trend
    assert not contains_forbidden(trend)
