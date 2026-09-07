"""Tape-to-cloud migration tool.

Working MVP: ``python -m tape_to_cloud ingest PATH`` copies real files, writes
pre/post SHA-256, an append-only chain-of-custody log, optional WORM lock, and
stdlib .eml/.mbox extract. Monetize is a separate broker layer.

This does not drive LTO libraries. Disk ingest is the live path.
"""

from . import monetize
from tape_to_cloud.core import MODULES, PlatformContext
from tape_to_cloud.core.registry import list_modules, submit_and_run

__all__ = ["MODULES", "PlatformContext", "list_modules", "submit_and_run", "monetize"]
__version__ = "0.2.0"
