"""Git rebase helper for bot PRs. Semantic conflicts are out of scope."""

from __future__ import annotations

import subprocess
from pathlib import Path


def rebase_onto_main(*, cwd: Path | None = None) -> dict[str, object]:
    root = cwd or Path.cwd()
    fetch = subprocess.run(  # noqa: S603
        ["git", "fetch", "origin", "main"],
        capture_output=True,
        text=True,
        cwd=str(root),
        check=False,
    )
    if fetch.returncode != 0:
        return {"ok": False, "stage": "fetch", "stderr": fetch.stderr}
    rebase = subprocess.run(  # noqa: S603
        ["git", "rebase", "origin/main"],
        capture_output=True,
        text=True,
        cwd=str(root),
        check=False,
    )
    if rebase.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], cwd=str(root), check=False, capture_output=True)  # noqa: S603
        return {
            "ok": False,
            "stage": "rebase",
            "comment": "@operator merge conflict on this PR — please resolve manually",
            "stderr": rebase.stderr,
        }
    return {"ok": True, "stage": "rebase"}
