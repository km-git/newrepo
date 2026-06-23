#!/usr/bin/env python3
"""
Autodream daemon — delegates to the live trading loop.

Prefer scripts/run_live_loop.py for new deployments.
This entry point remains for backward compatibility.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Re-use the unified live loop CLI
from scripts.run_live_loop import main

if __name__ == "__main__":
  main()
