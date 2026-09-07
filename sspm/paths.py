"""Working-directory path checks and literal tenant file maps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PKG = Path(__file__).resolve().parent
_FIXTURES = _PKG / "fixtures"
_BASELINES = _PKG / "baselines"

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


def load_fixture_json(tenant_type: str) -> dict[str, Any]:
    """Read a shipped fixture. Each branch reads a literal filename."""
    if tenant_type == "m365":
        return json.loads((_FIXTURES / "m365.json").read_text(encoding="utf-8"))
    if tenant_type == "gws":
        return json.loads((_FIXTURES / "gws.json").read_text(encoding="utf-8"))
    if tenant_type == "github":
        return json.loads((_FIXTURES / "github.json").read_text(encoding="utf-8"))
    if tenant_type == "slack":
        return json.loads((_FIXTURES / "slack.json").read_text(encoding="utf-8"))
    if tenant_type == "okta":
        return json.loads((_FIXTURES / "okta.json").read_text(encoding="utf-8"))
    raise ValueError(f"unknown tenant type: {tenant_type}")


def load_baseline_map(tenant_type: str) -> dict[str, str]:
    """Read shipped baseline settings. Each branch reads a literal filename."""
    if tenant_type == "m365":
        data = json.loads((_BASELINES / "m365.json").read_text(encoding="utf-8"))
    elif tenant_type == "gws":
        data = json.loads((_BASELINES / "gws.json").read_text(encoding="utf-8"))
    elif tenant_type == "github":
        data = json.loads((_BASELINES / "github.json").read_text(encoding="utf-8"))
    elif tenant_type == "slack":
        data = json.loads((_BASELINES / "slack.json").read_text(encoding="utf-8"))
    elif tenant_type == "okta":
        data = json.loads((_BASELINES / "okta.json").read_text(encoding="utf-8"))
    else:
        raise ValueError(f"unknown tenant type: {tenant_type}")
    settings = data.get("settings") or {}
    return {str(key): str(value) for key, value in settings.items()}


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
    cwd = Path.cwd().resolve()
    if tenant_type == "m365":
        return cwd / "output" / "sspm" / "m365_report.html"
    if tenant_type == "gws":
        return cwd / "output" / "sspm" / "gws_report.html"
    if tenant_type == "github":
        return cwd / "output" / "sspm" / "github_report.html"
    if tenant_type == "slack":
        return cwd / "output" / "sspm" / "slack_report.html"
    if tenant_type == "okta":
        return cwd / "output" / "sspm" / "okta_report.html"
    raise ValueError(f"unknown tenant type: {tenant_type}")


def report_md_file(tenant_type: str) -> Path:
    cwd = Path.cwd().resolve()
    if tenant_type == "m365":
        return cwd / "output" / "sspm" / "m365_report.md"
    if tenant_type == "gws":
        return cwd / "output" / "sspm" / "gws_report.md"
    if tenant_type == "github":
        return cwd / "output" / "sspm" / "github_report.md"
    if tenant_type == "slack":
        return cwd / "output" / "sspm" / "slack_report.md"
    if tenant_type == "okta":
        return cwd / "output" / "sspm" / "okta_report.md"
    raise ValueError(f"unknown tenant type: {tenant_type}")


def report_write_path(output: Path | str | None) -> Path:
    """Return a report destination built from cwd + an allowlisted filename."""
    cwd = Path.cwd().resolve()
    if output is None:
        dest = cwd / "output" / "sspm" / "report.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest
    raw = Path(output)
    if raw.is_absolute():
        resolved = raw.resolve()
        if not resolved.is_relative_to(cwd):
            raise ValueError("refusing path outside the working directory")
    dest = _literal_named_report(cwd, raw.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def _literal_named_report(cwd: Path, name: str) -> Path:
    if name == "report.md":
        return cwd / "report.md"
    if name == "m365_report.md":
        return cwd / "output" / "sspm" / "m365_report.md"
    if name == "gws_report.md":
        return cwd / "output" / "sspm" / "gws_report.md"
    if name == "github_report.md":
        return cwd / "output" / "sspm" / "github_report.md"
    if name == "slack_report.md":
        return cwd / "output" / "sspm" / "slack_report.md"
    if name == "okta_report.md":
        return cwd / "output" / "sspm" / "okta_report.md"
    raise ValueError(f"unsupported report filename: {name}")


def explorer_html_path(output_dir: str = "reports") -> Path:
    cwd = Path.cwd().resolve()
    if output_dir == "reports":
        return cwd / "reports" / EXPLORER_HTML_NAME
    return cwd / EXPLORER_HTML_NAME


def explorer_state_path() -> Path:
    return Path.cwd().resolve() / "output" / "sspm" / "explorer_state.json"


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
