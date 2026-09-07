"""AI security CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.ai_security.service import scan_vectorstore

app = typer.Typer(help="AI workload data security (experimental)")


@app.command("scan-vectorstore")
def scan_cmd(
    uri: str = typer.Argument(..., help="e.g. pgvector://localhost:5432/embeddings"),
    export: Path | None = typer.Option(None, "--export"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Scan vector-store prompt logs for sensitive content."""
    emit(scan_vectorstore(uri, export), human=human, title="AI Security Findings")
