"""RepoMix-style repository packer — minifies code for LLM agent context.

Packs source files into a single XML-tagged bundle with tree summary,
stripping comments/blank lines where safe to reduce token load.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Iterable, List, Set

DEFAULT_INCLUDE = (
  "ew_tool.py",
  "engine/",
  "core/",
  "fetchers/",
  "gateway/",
  "cache/",
  "schemas/",
  "scripts/",
)

DEFAULT_EXCLUDE_DIRS = {
  ".git",
  ".venv",
  "__pycache__",
  ".cache",
  "node_modules",
  "libs",
  "output",
  "reports",
  ".pytest_cache",
}

DEFAULT_EXCLUDE_FILES = {
  ".pyc",
  ".zst",
  ".json",
  ".csv",
  ".html",
  ".md",
}


def _should_skip(path: Path, root: Path) -> bool:
  rel = path.relative_to(root)
  for part in rel.parts:
    if part in DEFAULT_EXCLUDE_DIRS:
      return True
  if path.suffix in DEFAULT_EXCLUDE_FILES and path.name != "ew_tool.py":
    return True
  return False


def _minify_python(text: str) -> str:
  """Light minify: drop full-line comments and excess blank lines."""
  lines: List[str] = []
  blank_run = 0
  for line in text.splitlines():
    stripped = line.rstrip()
    if stripped.startswith("#") and not stripped.startswith("#!"):
      continue
    if not stripped:
      blank_run += 1
      if blank_run <= 1:
        lines.append("")
      continue
    blank_run = 0
    lines.append(stripped)
  return "\n".join(lines).strip() + "\n"


def collect_files(root: Path, includes: Iterable[str]) -> List[Path]:
  files: List[Path] = []
  seen: Set[Path] = set()
  for inc in includes:
    p = root / inc
    if p.is_file() and p not in seen:
      if not _should_skip(p, root):
        files.append(p)
        seen.add(p)
    elif p.is_dir():
      for f in sorted(p.rglob("*")):
        if f.is_file() and f.suffix == ".py" and f not in seen:
          if not _should_skip(f, root):
            files.append(f)
            seen.add(f)
  return sorted(files, key=lambda x: str(x))


def pack_repository(
  root: Path | str = ".",
  includes: Iterable[str] = DEFAULT_INCLUDE,
  minify: bool = True,
) -> str:
  root = Path(root).resolve()
  files = collect_files(root, includes)
  tree_lines = [f"  {f.relative_to(root)}" for f in files]
  parts = [
    "<repomix>",
    f"<repository>{root.name}</repository>",
    f"<file_count>{len(files)}</file_count>",
    "<directory_structure>",
    *tree_lines,
    "</directory_structure>",
  ]
  total_chars = 0
  for f in files:
    rel = f.relative_to(root)
    try:
      text = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
      continue
    if minify and f.suffix == ".py":
      text = _minify_python(text)
    total_chars += len(text)
    parts.extend(
      [
        f'<file path="{rel}">',
        text,
        "</file>",
      ]
    )
  parts.append(f"<total_source_chars>{total_chars}</total_source_chars>")
  parts.append("</repomix>")
  return "\n".join(parts)


def main() -> None:
  parser = argparse.ArgumentParser(description="RepoMix-style pack for agent context")
  parser.add_argument("--root", default=".", help="Repository root")
  parser.add_argument("--out", default="output/repomix_pack.xml", help="Output path")
  parser.add_argument("--no-minify", action="store_true", help="Skip comment stripping")
  parser.add_argument(
    "--include",
    action="append",
    default=None,
    help="Path or glob root to include (repeatable)",
  )
  args = parser.parse_args()
  includes = args.include or list(DEFAULT_INCLUDE)
  packed = pack_repository(args.root, includes, minify=not args.no_minify)
  out = Path(args.out)
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(packed, encoding="utf-8")
  print(f"[repomix] packed {len(includes)} roots → {out} ({len(packed):,} chars)")


if __name__ == "__main__":
  main()
