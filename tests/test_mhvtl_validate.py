from pathlib import Path
import importlib.util
import os

VALIDATE_PATH = Path(__file__).resolve().parents[1] / "forum-watcher" / "scripts" / "validate.py"


def _load():
    spec = importlib.util.spec_from_file_location("mhvtl_validate", VALIDATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_github_hosted_skips_tape_even_if_sg_claimed(monkeypatch, tmp_path):
    val = _load()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_ENVIRONMENT", "github-hosted")
    monkeypatch.delenv("RUNNER_LABELS", raising=False)
    monkeypatch.setenv("ImageOS", "ubuntu24")
    assert val.is_github_hosted() is True
    blocked = val.refuse_hosted_tape("mhvtl discovery")
    assert blocked["status"] == "skip"
    assert "GitHub-hosted" in blocked["detail"]


def test_self_hosted_label_is_not_github_hosted(monkeypatch):
    val = _load()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_LABELS", "self-hosted,linux,mhvtl")
    assert val.is_github_hosted() is False


def test_should_run_only_tape_modules():
    val = _load()
    assert val.should_run(["tape-ops"]) is True
    assert val.should_run(["vtl-cloud", "restore"]) is True
    assert val.should_run(["restore", "monetize"]) is False


def test_sha256_round_trip(tmp_path):
    val = _load()
    path = tmp_path / "x.bin"
    path.write_bytes(b"abc123")
    assert val.sha256_file(path) == val.sha256_file(path)
    other = tmp_path / "y.bin"
    other.write_bytes(b"abc124")
    assert val.sha256_file(path) != val.sha256_file(other)


def test_borg_or_skip():
    val = _load()
    outcome = val.test_borg_restore()
    assert outcome["status"] in {"pass", "skip"}
    if outcome["status"] == "skip":
        assert "borg" in outcome["detail"]


def test_tape_discovery_skips_without_sg(monkeypatch):
    val = _load()
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("RUNNER_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RUNNER_LABELS", raising=False)
    monkeypatch.setattr(val, "has_sg", lambda: False)
    monkeypatch.setattr(val, "is_github_hosted", lambda: False)
    outcome = val.test_mhvtl_discovery()
    assert outcome["status"] == "skip"
    assert "sg" in outcome["detail"]
