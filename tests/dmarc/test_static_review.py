from __future__ import annotations

from pathlib import Path

from dmarc.loop.static_review import MARKER, collect, render_markdown, scan_tls


def test_static_review_clean_on_dmarc_tls() -> None:
    root = Path(__file__).resolve().parents[2]
    tls = scan_tls(root)
    assert tls == []
    report = collect(root)
    markdown = render_markdown(report)
    assert MARKER in markdown
    assert "Bugbot replacement" in markdown
    assert "@CodiumAI-Agent /review" in markdown
    assert report["ok"] is True
