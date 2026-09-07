"""Loop / watcher tests."""

from cost.loop.classify import classify_item
from cost.loop.monthly import generate_monthly
from cost.loop.watch import url_digest, watch


def test_url_digest_stable():
    assert url_digest("https://example.com/a/") == url_digest("https://example.com/a")


def test_classify_finops():
    result = classify_item({"title": "FinOps rightsizing with Steampipe", "summary": "", "module_hint": "cost/rightsizing"})
    assert result["verdict"] in {"discover", "watch"}


def test_watch_offline():
    out = watch(fetch=False)
    assert out["new_count"] >= 1


def test_monthly_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = generate_monthly(out_dir=tmp_path / "monthly")
    assert (tmp_path / "monthly").exists()
    assert "rollup" in paths
    assert "cost_trend" in paths
