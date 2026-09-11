"""Continuous-improvement cycle: catalog gap-audit, GitHub/PyPI discover, 4-axis rubric."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_covers_four_categories() -> None:
    from dspm.loop.gap_audit import load_catalog

    items = load_catalog()
    cats = {i["category"] for i in items}
    assert cats == {"forum", "github_tool", "other_tool", "python_lib"}
    assert len(items) >= 20
    assert any(i["id"] == "gh_piicatcher" for i in items)
    assert any(i["id"] == "lib_dataprofiler" for i in items)
    assert any(i["id"] == "gh_cartography" for i in items)
    assert all(i.get("url") for i in items)


def test_gap_audit_names_next_integrations() -> None:
    from dspm.loop.gap_audit import audit

    report = audit()
    assert report["summary"]["gaps"] >= 5
    assert report["summary"]["by_category"]["github_tool"]["missing"] >= 1
    assert report["summary"]["by_category"]["python_lib"]["missing"] >= 1
    ids = [i["id"] for i in report["next_integrations"]]
    assert "lib_dataprofiler" in ids or "gh_dataprofiler" in ids
    assert "gh_cartography" in ids or "gh_cloudsplaining" in ids
    assert all(i.get("status") in {"missing", "partial"} for i in report["top_gaps"])
    for item in report["next_integrations"]:
        assert item["first_commit"]
        assert item["url"].startswith("http")


def test_evaluate_rubric_threshold() -> None:
    from dspm.loop.evaluate import evaluate_item

    hot = evaluate_item(
        {
            "title": "DataProfiler detects PII in CSV",
            "summary": "Apache-2.0 data classification library",
            "module_hint": "dspm/classification",
            "license": "Apache-2.0",
            "category": "python_lib",
            "url": "https://pypi.org/project/DataProfiler/",
        }
    )
    assert hot["score"] >= 7
    assert hot["verdict"] == "discover"
    assert set(hot["axes"]) == {"module_fit", "signal", "license", "actionability"}
    skip = evaluate_item(
        {
            "title": "Microsoft Purview commercial DSPM",
            "summary": "proprietary cloud DLP",
            "module_hint": "dspm/classification",
            "license": "proprietary",
            "category": "other_tool",
        }
    )
    assert skip["verdict"] == "skip"
    assert skip["axes"]["license"] == 0


def test_github_and_pypi_fixtures() -> None:
    from dspm.loop.github_discover import discover_github
    from dspm.loop.pypi_discover import discover_pypi

    gh = discover_github(fixture=ROOT / "examples" / "loop" / "github_search.json")
    names = {i["title"] for i in gh}
    assert "tokern/piicatcher" in names
    assert "lyft/cartography" in names
    assert all(i["license"] for i in gh)
    pypi = discover_pypi(fixture=ROOT / "examples" / "loop" / "pypi.json")
    assert {i["pypi"] for i in pypi} >= {"DataProfiler", "policyuniverse", "detect-secrets"}


def test_improve_cycle_offline(tmp_path: Path) -> None:
    from dspm.loop.improve import improve

    result = improve(
        fetch=False,
        github_fixture=ROOT / "examples" / "loop" / "github_search.json",
        pypi_fixture=ROOT / "examples" / "loop" / "pypi.json",
        seen_path=tmp_path / "seen.json",
        queue_path=tmp_path / "queue.json",
        candidates_path=tmp_path / "candidates.md",
        audit_path=tmp_path / "gap.json",
    )
    assert result["github"] >= 3
    assert result["pypi"] >= 3
    assert result["discover"] >= 1
    assert result["gaps"] >= 5
    md = (tmp_path / "candidates.md").read_text(encoding="utf-8")
    assert "DSPM next integrations" in md
    assert "Gap-audit next integrations" in md
    assert "https://" in md


def test_column_heuristics_on_headers() -> None:
    from dspm.classification.column_heuristics import classify_columns

    hits = classify_columns(["email", "tfn", "notes"], source="customers.csv")
    types = {h.type for h in hits}
    assert "PII" in types
    assert "custom" in types
    assert any(h.location.endswith(":schema") for h in hits)


def test_sources_include_github_pypi_and_lobsters() -> None:
    text = (ROOT / "dspm" / "loop" / "sources.yaml").read_text(encoding="utf-8")
    for needle in (
        "lobste.rs/t/security.rss",
        "trackawesomelist.com/rss.xml",
        "pypi.org/rss/project/DataProfiler",
        "lyft/cartography",
        "gitleaks/gitleaks",
        "google/osv-scanner",
        "tokern/piicatcher",
    ):
        assert needle in text
