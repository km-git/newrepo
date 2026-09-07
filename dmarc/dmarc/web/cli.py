"""Web UI CLI."""

from __future__ import annotations

import typer

app = typer.Typer(help="DMARC web dashboard")


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8767, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Start FastAPI dashboard."""
    import uvicorn

    typer.echo(f"DMARC Web UI → http://127.0.0.1:{port}")
    typer.echo(f"API docs → http://127.0.0.1:{port}/api/docs")
    uvicorn.run("dmarc.web.app:app", host=host, port=port, reload=reload)
