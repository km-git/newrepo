from pathlib import Path
import importlib.util
import json

MONTHLY_PATH = Path(__file__).resolve().parents[1] / "forum-watcher" / "scripts" / "monthly.py"


def _load():
    spec = importlib.util.spec_from_file_location("monthly_rollup", MONTHLY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_discoveries(tmp_path):
    monthly = _load()
    md = tmp_path / "2026-09-08.md"
    md.write_text(
        "# Discoveries — week of 2026-09-08\n\n"
        "- [ ] **[tape-ops]** [NetBackup 10.0 notes](https://example.com/nbu)\n"
        "  r/netbackup · score 8 · vendor release\n"
        "- [x] **[restore]** [VBR how-to](https://example.com/vbr)\n"
        "  r/Veeam · score 7 · checked\n"
    )
    items = monthly.parse_discoveries(tmp_path)
    assert len(items) == 2
    assert items[0]["source"] == "r/netbackup"
    assert items[1]["checked"] is True


def test_community_shift_and_ratios():
    monthly = _load()
    previous = [
        {"source": "r/homelab", "decision": "accept", "month": "2026-08"},
        {"source": "r/homelab", "decision": "accept", "month": "2026-08"},
        {"source": "r/homelab", "decision": "accept", "month": "2026-08"},
        {"source": "r/homelab", "decision": "reject", "month": "2026-08"},
    ]
    current = [
        {"source": "r/homelab", "decision": "reject", "month": "2026-09"},
        {"source": "r/homelab", "decision": "reject", "month": "2026-09"},
        {"source": "r/homelab", "decision": "reject", "month": "2026-09"},
        {"source": "r/homelab", "decision": "accept", "month": "2026-09"},
    ]
    flips = monthly.community_shifts(
        monthly.accept_ratio(current),
        monthly.accept_ratio(previous),
    )
    assert flips and flips[0]["source"] == "r/homelab"


def test_render_contains_required_sections(tmp_path):
    monthly = _load()
    items = [
        {
            "source": "cvpysdk releases",
            "title": "Release 12.0.0",
            "url": "https://github.com/Commvault/cvpysdk/releases/tag/v12.0.0",
            "file": "2026-09-01.md",
        }
    ]
    md = monthly.render("2026-09", items, [], ["mhvtl", "borg"])
    assert "Top 10 most-cited sources" in md
    assert "cvpysdk releases" in md
    assert "Vendor major-version crossings" in md
    assert "12.0" in md or "Release 12.0.0" in md


def test_accept_jsonl_round_trip(tmp_path):
    monthly = _load()
    path = tmp_path / "accept-reject.jsonl"
    path.write_text(
        json.dumps({"source": "r/netbackup", "decision": "accept", "month": "2026-09"}) + "\n"
    )
    rows = monthly.load_decisions(path)
    stats = monthly.accept_ratio(rows)
    assert stats["r/netbackup"]["ratio"] == 1.0
