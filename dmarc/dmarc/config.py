"""Paths and environment configuration for the DMARC package."""

from __future__ import annotations

import os
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PKG_ROOT.parent
DATA_DIR = Path(os.environ.get("DMARC_DATA_DIR", PROJECT_ROOT / "output"))
DB_PATH = Path(os.environ.get("DMARC_DB_PATH", DATA_DIR / "dmarc.duckdb"))
REPORTS_DIR = Path(os.environ.get("DMARC_REPORTS_DIR", PROJECT_ROOT / "reports"))
SAMPLES_DIR = PROJECT_ROOT / "samples"
DISCLAIMER_PATH = PROJECT_ROOT / "disclaimers" / "disclaimer_au.txt"
DEFAULT_DOMAIN = os.environ.get("DMARC_DOMAIN", "example.com.au")

DEFAULT_DKIM_SELECTORS = (
    "google",
    "selector1",
    "selector2",
    "k1",
    "s1",
    "s2",
    "cm",
    "default",
)

DISALLOWED_WORDS = frozenset(
    {"compliance", "attestation", "certified", "secure", "guaranteed", "guarantees"}
)
