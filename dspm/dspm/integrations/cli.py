"""Integrations CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.integrations.github import list_org_repos, scan_repo

app = typer.Typer(help="GitHub repo scanning and org inventory")


@app.command("scan-repo")
def scan_repo_cmd(
    owner: str = typer.Argument(...),
    repo: str = typer.Argument(...),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit(scan_repo(owner, repo), human=human, title=f"GitHub Scan: {owner}/{repo}")


@app.command("list-repos")
def list_repos_cmd(
    org: str = typer.Argument(...),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit(list_org_repos(org), human=human, title=f"Repos: {org}")
