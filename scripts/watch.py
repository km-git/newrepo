"""Thin wrapper so prior-turn `scripts/watch.py` imports keep working."""

from __future__ import annotations

import json
import sys

from dspm.loop.watch import watch


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    mode = "all"
    if "--mode" in args:
        mode = args[args.index("--mode") + 1]
    result = watch(mode=mode, fetch="--fetch" in args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
