"""FastAPI web dashboard for DMARC deliverability review."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dmarc.config import DEFAULT_DOMAIN, REPORTS_DIR
from dmarc.db import count_rows, fetch_all, init_db
from dmarc.report_writer.service import generate_report

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"


def _json_safe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for key, val in row.items():
            if hasattr(val, "isoformat"):
                item[key] = val.isoformat()
            else:
                item[key] = val
        safe.append(item)
    return safe


def _dashboard_payload(domain: str = DEFAULT_DOMAIN) -> dict:
    return {
        "domain": domain,
        "counts": {
            "dns": count_rows("findings_dns"),
            "spf": count_rows("findings_spf"),
            "dkim": count_rows("findings_dkim"),
            "dmarc": count_rows("findings_dmarc"),
            "forensic": count_rows("findings_forensic"),
            "inbox": count_rows("findings_inbox"),
        },
        "dns": _json_safe(fetch_all("findings_dns", limit=20)),
        "spf": _json_safe(fetch_all("findings_spf", limit=5)),
        "dkim": _json_safe(fetch_all("findings_dkim", limit=10)),
        "dmarc": _json_safe(fetch_all("findings_dmarc", limit=20)),
        "inbox": _json_safe(fetch_all("findings_inbox", limit=10)),
        "reports_dir": str(REPORTS_DIR),
    }


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    if count_rows("findings_dns") == 0:
        from dmarc.cli import scan_cmd

        scan_cmd(domain=DEFAULT_DOMAIN)
    yield


app = FastAPI(
    title="DMARC Deliverability Monitor",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data": _dashboard_payload()},
    )


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "dmarc-web", "version": "0.1.0"}


@app.get("/api/dashboard")
async def api_dashboard(domain: str = DEFAULT_DOMAIN) -> JSONResponse:
    return JSONResponse(_dashboard_payload(domain))


@app.post("/api/scan")
async def api_scan(domain: str = DEFAULT_DOMAIN) -> JSONResponse:
    from dmarc.config import DEFAULT_DKIM_SELECTORS
    from dmarc.dkim_check.service import check_all_selectors
    from dmarc.dmarc_ingest.service import ingest_reports
    from dmarc.dns_check.service import check_domain
    from dmarc.inbox_placement.service import run_inbox_test
    from dmarc.spf_parser.service import parse_spf

    check_domain(domain)
    parse_spf(domain)
    check_all_selectors(domain, list(DEFAULT_DKIM_SELECTORS))
    ingest_reports(domain, demo=True)
    run_inbox_test(f"noreply@{domain}", ["seed@gmail.com"], demo=True)
    md, js = generate_report(domain)
    payload = _dashboard_payload(domain)
    payload["report_md"] = str(md)
    payload["report_json"] = str(js)
    return JSONResponse(payload)
