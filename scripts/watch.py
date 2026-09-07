#!/usr/bin/env python3
"""Backward-compat wrapper for SSPM forum watcher."""

from sspm.loop.watch import watch

if __name__ == "__main__":
    import json
    import sys

    fetch = "--fetch" in sys.argv
    print(json.dumps(watch(fetch=fetch), indent=2))
