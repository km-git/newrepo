from pathlib import Path

from licensespend.privacy import contains_raw_email
from licensespend.report.service import build, verify_watermark


def test_report_watermark_and_no_email(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LICENSESPEND_INCLUDE_EMAIL", raising=False)
    files = build(client="fixture", out_dir=tmp_path)
    assert verify_watermark(Path(files.json_path))
    for path in (files.json_path, files.markdown_path, files.html_path):
        text = Path(path).read_text(encoding="utf-8")
        assert not contains_raw_email(text)
        assert files.watermark in text or path.endswith(".json")
    assert files.reclaim_monthly_aud == 127.0
