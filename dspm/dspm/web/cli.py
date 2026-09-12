"""Web UI CLI."""

from __future__ import annotations

import typer

app = typer.Typer(help="DSPM web dashboard")


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8766, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Start the DSPM web UI (FastAPI + dashboard)."""
    import uvicorn

    typer.echo(f"DSPM Web UI → http://127.0.0.1:{port}")
    uvicorn.run("dspm.web.app:app", host=host, port=port, reload=reload)
