"""Zero-key Bugbot replacement: Ruff + Bandit-equivalent S + TLS/workflow heuristics.

Posts a Markdown review (CI) or prints it (local). No LLM, no API key, no Bugbot retry.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MARKER = "<!-- static-review-bugbot-replacement -->"

_IMAP_RE = re.compile(r"IMAP4_SSL\s*\(")
_STARTTLS_RE = re.compile(r"\.starttls\s*\(")
_MAIN_PIN_RE = re.compile(r"uses:\s+\S+@main\b")
SKIP_DIRS = {".git", ".venv", "output", ".cache", "__pycache__", ".pytest_cache", "libs"}


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def scan_tls(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_files(root / "dmarc", (".py",)):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root)
        for i, line in enumerate(text.splitlines(), 1):
            if _IMAP_RE.search(line) and "ssl_context" not in line:
                findings.append(
                    {
                        "severity": "high",
                        "path": str(rel),
                        "line": i,
                        "rule": "tls-imap",
                        "message": "IMAP4_SSL must pass ssl.create_default_context() via ssl_context=",
                    }
                )
            if _STARTTLS_RE.search(line) and "context=" not in line:
                findings.append(
                    {
                        "severity": "high",
                        "path": str(rel),
                        "line": i,
                        "rule": "tls-starttls",
                        "message": "SMTP starttls() must pass context=ssl.create_default_context()",
                    }
                )
    return findings


def scan_workflows(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return findings
    for path in sorted(workflows.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root)
        for i, line in enumerate(text.splitlines(), 1):
            if _MAIN_PIN_RE.search(line):
                findings.append(
                    {
                        "severity": "high",
                        "path": str(rel),
                        "line": i,
                        "rule": "action-main-pin",
                        "message": "GitHub Action pinned to @main; pin a release tag or commit SHA",
                    }
                )
    return findings


def scan_ruff(root: Path) -> dict[str, Any]:
    binary = shutil.which("ruff")
    venv = root / ".venv" / "bin" / "ruff"
    cmd = str(venv) if venv.exists() else binary
    if not cmd:
        return {"ok": True, "skipped": True, "output": "ruff not installed"}
    paths = ["dmarc", "tests/dmarc", "scripts/serve_dmarc.py"]
    existing = [p for p in paths if (root / p).exists()]
    proc = subprocess.run(  # noqa: S603 — ruff binary, argv list, no shell
        [cmd, "check", "--config", str(root / "ruff.toml"), *existing],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return {"ok": proc.returncode == 0, "skipped": False, "output": output.strip(), "code": proc.returncode}


def collect(root: Path) -> dict[str, Any]:
    tls = scan_tls(root)
    workflows = scan_workflows(root)
    ruff = scan_ruff(root)
    findings = tls + workflows
    return {
        "ruff": ruff,
        "findings": findings,
        "ok": bool(ruff.get("ok")) and not findings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    ruff = report.get("ruff") or {}
    findings = report.get("findings") or []
    ruff_line = "skipped" if ruff.get("skipped") else ("pass" if ruff.get("ok") else "FAIL")
    tls_status = "pass" if not any(str(f.get("rule", "")).startswith("tls") for f in findings) else "FAIL"
    pin_status = "pass" if not any(f.get("rule") == "action-main-pin" for f in findings) else "FAIL"
    stack = (
        "Zero-key GitHub stack: **Ruff** (`E,F,W,I,UP,B,SIM,RUF,S` Bandit-equivalent) + **gitleaks** + "
        + "**zizmor** + **actionlint** + **OSV-Scanner** + **pip-audit** + **detect-secrets** + **CodeQL**."
    )
    codium = (
        "Public-repo AI narrative: comment `@CodiumAI-Agent /review`, or install CodeRabbit from the "
        + "GitHub Marketplace (~4 PRs/hr, no workflow file)."
    )
    lines = [
        MARKER,
        "# Static review (Bugbot replacement)",
        "",
        stack,
        "No LLM. Do not retry Cursor Bugbot after a usage-cap skip.",
        codium,
        "",
        f"- Ruff: `{ruff_line}`",
        f"- TLS / IMAP / STARTTLS: `{tls_status}`",
        f"- Workflow `@main` pins: `{pin_status}`",
        "",
    ]
    if findings:
        lines.append("## Findings")
        lines.append("")
        for item in findings:
            lines.append(f"- `{item['severity']}` `{item['path']}:{item['line']}` `{item['rule']}` — {item['message']}")
        lines.append("")
    else:
        lines.append("No heuristic findings.")
        lines.append("")
    if not ruff.get("ok") and ruff.get("output"):
        lines.extend(["## Ruff output", "", "```", str(ruff.get("output"))[:4000], "```", ""])
    lines.append("This comment is updated in place on each push (`static-review` workflow).")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zero-key Bugbot replacement static review")
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--output", default="", help="Write Markdown to this path")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = collect(root)
    markdown = render_markdown(report)
    if args.output:
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
