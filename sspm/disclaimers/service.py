"""Liability disclaimer text. Auto-merge of this tree is forbidden."""

from __future__ import annotations

from pathlib import Path

from sspm.disclaimers.models import Disclaimer

DIR = Path(__file__).resolve().parent
KNOWN = {
    "disclaimer_au": DIR / "disclaimer_au.txt",
    "active_work_referral": DIR / "active_work_referral.txt",
}


def show(name: str = "disclaimer_au") -> Disclaimer:
    path = KNOWN.get(name)
    if path is None or not path.exists():
        raise KeyError(f"unknown disclaimer {name!r}")
    return Disclaimer(name=name, text=path.read_text(encoding="utf-8"), path=str(path))


def append_to(report: str, name: str = "disclaimer_au") -> str:
    block = show(name).text.strip()
    if block in report:
        return report
    return report.rstrip() + "\n\n---\n\n## Liability disclaimer\n\n" + block + "\n"
