"""Loop / watcher tests for the cost improvement loop."""

from pathlib import Path

from cost.loop.service import monthly_rollup, run


def test_loop_sandbox_runs():
    result = run(sandbox=True)
    assert result["ok"] is True
    assert result["watcher_imported"] is True


def test_monthly_rollup_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("COST_SANDBOX", "1")
    monkeypatch.setenv("COST_DB", str(tmp_path / "cost.sqlite3"))
    monkeypatch.chdir(tmp_path)
    paths = monthly_rollup()
    assert paths["ok"] is True
    assert Path(paths["month"]).exists()
    assert Path(paths["trend"]).exists()
