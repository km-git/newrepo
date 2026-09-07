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


def test_mode_filters_vendor_vs_community():
    watch = _load_watch()
    sources = [
        {"name": "r/sysadmin", "group": "community"},
        {"name": "r/netbackup", "group": "vendor"},
    ]
    assert [s["name"] for s in watch.filter_sources(sources, "community")] == ["r/sysadmin"]
    assert [s["name"] for s in watch.filter_sources(sources, "vendor")] == ["r/netbackup"]
    assert len(watch.filter_sources(sources, "all")) == 2


def test_vendor_prompt_includes_jargon_block():
    watch = _load_watch()
    prompt = watch.classify_prompt(
        {
            "title": "VBR 12.3 VONE dashboard",
            "summary": "Helios vs CommCell notes",
            "source": "r/veeam",
            "url": "https://example.com/vbr",
            "group": "vendor",
            "vendor": "veeam",
            "module_hint": "vtl-cloud, restore",
        }
    )
    assert "BEX = BackupExec" in prompt
    assert "VBR = Veeam Backup & Replication" in prompt
    community = watch.classify_prompt(
        {
            "title": "LTFS mount how-to",
            "summary": "tape",
            "source": "r/sysadmin",
            "url": "https://example.com/ltfs",
            "group": "community",
            "module_hint": "tape-ops",
        }
    )
    assert "BEX = BackupExec" not in community


def test_canonical_url_drops_shorteners():
    watch = _load_watch()
    assert watch.canonical_url("https://t.co/abc") is None
    assert watch.canonical_url("https://github.com/borgbackup/borg") == (
        "https://github.com/borgbackup/borg"
    )


def test_vendor_heuristic_does_not_zero_fit_on_jargon():
    watch = _load_watch()
    result = watch.heuristic_classify(
        {
            "title": "CommCell MTree backup to DD Boost",
            "summary": "Helios policy and VBR comparison",
            "source": "r/commvault",
            "group": "vendor",
            "vendor": "commvault",
            "module_hint": "tape-ops, tape-vault",
            "url": "https://example.com/cc",
        }
    )
    assert result["module"] in {"tape-ops", "tape-vault"}
    assert result["score"] >= 5


def test_eighteen_tools_inventory():
    watch = _load_watch()
    tools = watch.load_test_tools()
    names = {t["name"] for t in tools}
    assert len(tools) == 18
    assert "mhvtl" in names
    assert "SeaweedFS" in names
    assert "VeeamZIP" in names
    veeam = next(t for t in tools if t["name"] == "VeeamZIP")
    assert veeam.get("windows_only") is True


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
