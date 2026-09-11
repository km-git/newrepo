from pathlib import Path
import importlib.util

WATCH_PATH = Path(__file__).resolve().parents[1] / "forum-watcher" / "scripts" / "watch.py"


def _load_watch():
    spec = importlib.util.spec_from_file_location("forum_watch", WATCH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_url_hash_is_sha256_hex():
    watch = _load_watch()
    digest = watch.url_hash("https://example.com/a")
    assert digest == watch.url_hash("https://example.com/a")
    assert digest != watch.url_hash("https://example.com/b")
    assert len(digest) == 64


def test_parse_algolia_uses_hn_item_fallback():
    watch = _load_watch()
    src = {"name": "HN", "max_items": 10, "module_hint": "tape-ops"}
    items = watch.parse_algolia(
        {
            "hits": [
                {"objectID": "123", "title": "LTFS on LTO-9", "url": None, "created_at": "2026-09-01"}
            ]
        },
        src,
    )
    assert items[0]["url"] == "https://news.ycombinator.com/item?id=123"
    assert items[0]["title"] == "LTFS on LTO-9"


def test_parse_rss_atom_entries():
    watch = _load_watch()
    atom = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Release 1.4.5</title>
        <link href="https://github.com/borgbackup/borg/releases/tag/1.4.5"/>
        <id>https://github.com/borgbackup/borg/releases/tag/1.4.5</id>
        <summary>bugfix</summary>
      </entry>
    </feed>
    """
    items = watch.parse_rss(atom, {"name": "borg releases", "max_items": 5, "module_hint": "disk-ingest"})
    assert len(items) == 1
    assert "1.4.5" in items[0]["title"]
    assert "github.com" in items[0]["url"]


def test_blocklist_and_heuristic_verdict():
    watch = _load_watch()
    assert watch.blocked("Tips for Burnout Recovery", "", ["burnout recovery"])
    assert not watch.blocked("LTFS mount how-to", "", ["burnout recovery"])
    item = {
        "title": "How to pip install libratom for PST extract",
        "summary": "working code for email-extract",
        "source": "r/sysadmin",
        "module_hint": "email-extract",
        "url": "https://example.com",
    }
    result = watch.heuristic_classify(item)
    assert result["verdict"] in {"discover", "watch"}
    assert result["score"] >= 5
    hinted_only = watch.heuristic_classify(
        {
            "title": "Day to day life of M365 admin",
            "summary": "office politics",
            "source": "r/sysadmin",
            "module_hint": "tape-ops, restore",
            "url": "https://example.com/offtopic",
        }
    )
    assert hinted_only["verdict"] != "discover"


def test_render_markdown_checkboxes():
    watch = _load_watch()
    classified = [
        {
            "title": "SeaweedFS 4.0",
            "url": "https://example.com/sw",
            "source": "HN",
            "classification": {
                "module": "tape-vault",
                "score": 8,
                "verdict": "discover",
                "reason": "s3 replacement",
            },
        }
    ]
    md = watch.render_markdown("2026-09-08", classified)
    assert "- [ ] **[tape-vault]** [SeaweedFS 4.0](https://example.com/sw)" in md
    assert "1 discover" in md


def test_forum_monitoring_doc_exists():
    doc = Path(__file__).resolve().parents[1] / "discovery" / "tape-to-cloud" / "forum-monitoring.md"
    text = doc.read_text(encoding="utf-8")
    assert "Australia/Sydney" in text
    assert "forum-watcher" in text
