#!/usr/bin/env python3
"""Generate cost module boilerplate (cli, models, tests, README)."""
from pathlib import Path

MODULES = [
    "audit",
    "aws_inventory",
    "azure_inventory",
    "gcp_inventory",
    "cost_explorer",
    "rightsizing",
    "untagged",
    "config_drift",
    "compliance_map",
    "report_writer",
    "multi_account",
]

ROOT = Path(__file__).resolve().parents[1] / "cost"

README = """# {name}

Cloud Cost & Configuration Review module. Read-only cost and configuration observations — not a security assessment.

Primary OSS: see `cost/constants.py`. Run via `cost` CLI or `make cost-all`.
"""

for name in MODULES:
    mod = ROOT / name
    mod.mkdir(parents=True, exist_ok=True)
    (mod / "__init__.py").write_text('"""Cost module."""\n', encoding="utf-8")
    (mod / "models.py").write_text(
        f'"""Pydantic models for {name}."""\n\nfrom pydantic import BaseModel, Field\n\n\n'
        f'class {name.title().replace("_", "")}Result(BaseModel):\n'
        f'    module: str = Field(default="{name}")\n'
        f'    ok: bool = True\n'
        f'    count: int = 0\n',
        encoding="utf-8",
    )
    (mod / "cli.py").write_text(
        f'"""CLI hooks for {name}."""\n\nfrom __future__ import annotations\n\n'
        f'import typer\n\napp = typer.Typer(help="{name} module")\n',
        encoding="utf-8",
    )
    tests = mod / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "test_smoke.py").write_text(
        f'def test_{name}_imports():\n'
        f'    from cost.{name} import service  # noqa: F401\n',
        encoding="utf-8",
    )
    (mod / "README.md").write_text(README.format(name=name), encoding="utf-8")

print(f"Scaffolded {len(MODULES)} modules under {ROOT}")
