"""cost/loop/watch.py — import prior watcher; add cost sources without duplicating it."""

from __future__ import annotations

from cost.loop.service import run


def main() -> int:
    result = run()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
