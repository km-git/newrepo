"""Working-directory path checks and literal tenant file maps."""

from __future__ import annotations

from pathlib import Path

_PKG = Path(__file__).resolve().parent
_FIXTURES = _PKG / "fixtures"

FIXTURE_FILES: dict[str, Path] = {
    "m365": _FIXTURES / "m365.json",
    "gws": _FIXTURES / "gws.json",
    "github": _FIXTURES / "github.json",
    "slack": _FIXTURES / "slack.json",
    "okta": _FIXTURES / "okta.json",
}

REPORT_MD: dict[str, Path] = {
    "m365": Path("output/sspm/m365_report.md"),
    "gws": Path("output/sspm/gws_report.md"),
    "github": Path("output/sspm/github_report.md"),
    "slack": Path("output/sspm/slack_report.md"),
    "okta": Path("output/sspm/okta_report.md"),
}

REPORT_HTML: dict[str, Path] = {
    "m365": Path("output/sspm/m365_report.html"),
    "gws": Path("output/sspm/gws_report.html"),
    "github": Path("output/sspm/github_report.html"),
    "slack": Path("output/sspm/slack_report.html"),
    "okta": Path("output/sspm/okta_report.html"),
}

EXPLORER_HTML_NAME = "sspm_explorer.html"
EXPLORER_STATE = Path("output/sspm/explorer_state.json")
DEFAULT_REPORT_MD = Path("output/sspm/report.md")


def under_workdir(path: Path | str) -> Path:
    """Resolve `path` and reject anything outside the current working directory."""
    raw = Path(path)
    cwd = Path.cwd().resolve()
    resolved = raw.resolve() if raw.is_absolute() else (cwd / raw).resolve()
    if not resolved.is_relative_to(cwd):
        raise ValueError("refusing path outside the working directory")
    return resolved


def fixture_file(tenant_type: str) -> Path:
    """Return the shipped fixture path. Branches use literals so callers cannot build paths."""
    if tenant_type == "m365":
        return _FIXTURES / "m365.json"
    if tenant_type == "gws":
        return _FIXTURES / "gws.json"
    if tenant_type == "github":
        return _FIXTURES / "github.json"
    if tenant_type == "slack":
        return _FIXTURES / "slack.json"
    if tenant_type == "okta":
        return _FIXTURES / "okta.json"
    raise ValueError(f"unknown tenant type: {tenant_type}")


def report_html_file(tenant_type: str) -> Path:
    if tenant_type == "m365":
        return under_workdir(Path("output/sspm/m365_report.html"))
    if tenant_type == "gws":
        return under_workdir(Path("output/sspm/gws_report.html"))
    if tenant_type == "github":
        return under_workdir(Path("output/sspm/github_report.html"))
    if tenant_type == "slack":
        return under_workdir(Path("output/sspm/slack_report.html"))
    if tenant_type == "okta":
        return under_workdir(Path("output/sspm/okta_report.html"))
    raise ValueError(f"unknown tenant type: {tenant_type}")


def report_md_file(tenant_type: str) -> Path:
    if tenant_type == "m365":
        return under_workdir(Path("output/sspm/m365_report.md"))
    if tenant_type == "gws":
        return under_workdir(Path("output/sspm/gws_report.md"))
    if tenant_type == "github":
        return under_workdir(Path("output/sspm/github_report.md"))
    if tenant_type == "slack":
        return under_workdir(Path("output/sspm/slack_report.md"))
    if tenant_type == "okta":
        return under_workdir(Path("output/sspm/okta_report.md"))
    raise ValueError(f"unknown tenant type: {tenant_type}")


def tenant_from_report_url(path: str) -> str | None:
    """Map an explorer URL onto a tenant literal. Unknown paths return None."""
    if path == "/sspm/report/m365":
        return "m365"
    if path == "/sspm/report/gws":
        return "gws"
    if path == "/sspm/report/github":
        return "github"
    if path == "/sspm/report/slack":
        return "slack"
    if path == "/sspm/report/okta":
        return "okta"
    return None
