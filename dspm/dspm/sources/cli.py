"""Sources CLI — unified multi-protocol discovery."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.sources.registry import SUPPORTED_SCHEMES, discover, preview
from dspm.sources.scanner import scan_and_classify

app = typer.Typer(help="Unified data sources: backup, NFS, SMB, S3, M365, SaaS")


@app.command("schemes")
def schemes_cmd(human: bool = typer.Option(False, "--human")) -> None:
    """List supported URI schemes."""
    emit({"schemes": SUPPORTED_SCHEMES}, human=human)


@app.command("discover")
def discover_cmd(
    uri: str = typer.Argument(..., help="e.g. file:///data, s3://bucket/, smb://server/share"),
    max_objects: int = typer.Option(200, "--max"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Discover objects at any supported source."""
    objects = discover(uri, max_objects=max_objects)
    emit([o.model_dump() for o in objects], human=human, title=f"Discovered ({len(objects)})")


@app.command("preview")
def preview_cmd(
    uri: str = typer.Argument(...),
    path: str = typer.Argument("", help="Object path within source"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Preview object content (first 8KB)."""
    emit(preview(uri, path).model_dump(), human=human)


@app.command("scan")
def scan_cmd(
    uri: str = typer.Argument(...),
    max_objects: int = typer.Option(200, "--max"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Discover + classify unstructured data at source."""
    result = scan_and_classify(uri, max_objects=max_objects)
    emit(
        {
            "source_uri": result.source_uri,
            "provider": result.provider,
            "object_count": result.object_count,
            "finding_count": len(result.findings),
            "objects": [o.model_dump() for o in result.objects[:20]],
            "findings": result.findings[:30],
        },
        human=human,
        title="Source Scan",
    )
