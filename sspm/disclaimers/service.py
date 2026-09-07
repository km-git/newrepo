"""Liability disclaimer text."""

from __future__ import annotations

from pathlib import Path

DISCLAIMERS_DIR = Path(__file__).resolve().parent


def load_disclaimer(name: str = "disclaimer_au") -> str:
    path = DISCLAIMERS_DIR / f"{name}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def show(name: str = "disclaimer_au") -> dict[str, str]:
    text = load_disclaimer(name)
    return {"name": name, "text": text, "length": str(len(text))}
