"""Forum-watcher dedupe, monthly rollup, and loop wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from dspm.loop.monthly import generate_monthly
from dspm.loop.watch import fetch_text, parse_rss, url_digest, watch


def test_url_digest_dedupes_fragments_and_trailing_slash() -> None:
    a = "https://github.com/cohesity/dataprotect-mock-cookies/"
    b = "https://github.com/cohesity/dataprotect-mock-cookies#readme"
    assert url_digest(a) == url_digest(b)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://example.com/rss.xml",
        "ftp://example.com/rss.xml",
        "https://",
        "not-a-url",
    ],
)
def test_fetch_text_refuses_non_https(url: str) -> None:
    with pytest.raises(ValueError, match="https"):
        fetch_text(url)


def test_parse_rss_items() -> None:
    xml = """
    <rss><channel>
      <item><title>DSPM tools</title><link>https://example.com/a</link><description>presidio</description></item>
      <item><title>Other</title><link>https://example.com/b</link><description>hello</description></item>
    </channel></rss>
    """
    items = parse_rss(xml, max_items=10)
    assert items[0]["title"] == "DSPM tools"
    assert items[0]["url"] == "https://example.com/a"


def test_watch_offline_discover_and_dedupe(tmp_path: Path) -> None:
    seen = tmp_path / "seen.json"
    first = watch(seen_path=seen, fixture_items=None)
    assert first["new_count"] == 1
    assert first["items"][0]["verdict"] in {"discover", "watch"}
    second = watch(seen_path=seen, fixture_items=None)
    assert second["new_count"] == 0


def test_monthly_writes_posture(tmp_path: Path) -> None:
    from dspm.db.store import FindingsStore

    db = tmp_path / "dspm.sqlite"
    store = FindingsStore(db)
    store.insert(
        "findings",
        {
            "source": "s3://public/customers.csv",
            "location": "email",
            "type": "PII",
            "confidence": 0.9,
            "verdict": "PII",
            "suggested_action": "mask",
            "extra": {},
            "created_at": "2026-09-07T00:00:00+00:00",
        },
    )
    log = tmp_path / "accept-reject.jsonl"
    log.write_text(
        '{"verdict":"discover","source":"r/cybersecurity"}\n{"verdict":"skip","source":"HN dspm"}\n',
        encoding="utf-8",
    )
    paths = generate_monthly(out_dir=tmp_path / "monthly", accept_log=log, db_path=db)
    posture = Path(paths["posture"]).read_text(encoding="utf-8")
    rollup = Path(paths["rollup"]).read_text(encoding="utf-8")
    assert "PII/PHI/PCI/custom findings: **1**" in posture
    assert "discover: 1" in rollup
    assert "r/cybersecurity" in rollup
