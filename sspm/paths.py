"""Working-directory path checks and literal tenant file maps."""

from __future__ import annotations

from pathlib import Path

from sspm import TENANT_TYPES

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
    path = FIXTURE_FILES.get(tenant_type)
    if path is None or tenant_type not in TENANT_TYPES:
        raise ValueError(f"unknown tenant type: {tenant_type}")
    return path


def report_html_file(tenant_type: str) -> Path:
    path = REPORT_HTML.get(tenant_type)
    if path is None:
        raise ValueError(f"unknown tenant type: {tenant_type}")
    return under_workdir(path)


def report_md_file(tenant_type: str) -> Path:
    path = REPORT_MD.get(tenant_type)
    if path is None:
        raise ValueError(f"unknown tenant type: {tenant_type}")
    return under_workdir(path)
