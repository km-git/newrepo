"""FastAPI web UI for SSPM reports and dashboard."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sspm.audit.service import inventory
from sspm.compliance_map.service import map_framework
from sspm.config_drift.service import diff
from sspm.db.store import FindingsStore
from sspm.disclaimers.service import load_disclaimer
from sspm.m365_discovery.service import discover as m365_discover
from sspm.multi_tenant.service import list_tenants
from sspm.oauth_grants.service import list_grants
from sspm.report_writer.service import generate

WEB_DIR = Path(__file__).resolve().parent
STATIC = WEB_DIR / "static"
TEMPLATES = WEB_DIR / "templates"
REPORTS = Path(__file__).resolve().parents[2] / "output" / "sspm"


def _demo_scan(tenant: str = "m365") -> dict:
    store = FindingsStore()
    inv = m365_discover("contoso.onmicrosoft.com", store=store) if tenant == "m365" else {"tenant": tenant}
    drift = diff(tenant)
    oauth = list_grants(tenant, store=store)
    refs = map_framework("cis-m365" if tenant == "m365" else "iso27001", tenant)
    report_path = REPORTS / f"report_{tenant}.md"
    result = generate(tenant, report_path, inventory=inv, drift=drift, oauth_grants=oauth, control_references=refs)
    return {
        "tenant": tenant,
        "inventory": inv,
        "drift": drift,
        "oauth_grants": oauth,
        "control_references": refs,
        "report": result,
        "disclaimer": load_disclaimer("disclaimer_au")[:200] + "...",
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    REPORTS.mkdir(parents=True, exist_ok=True)
    FindingsStore()
    yield


app = FastAPI(title="SSPM Configuration Report", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "sspm-web", "version": "0.1.0"}


@app.get("/api/inventory")
async def api_inventory() -> dict:
    return inventory()


@app.get("/api/tenants")
async def api_tenants() -> list:
    return list_tenants()


@app.get("/api/dashboard")
async def api_dashboard() -> dict:
    store = FindingsStore()
    tenants = store.fetchall("findings_tenants", limit=20)
    oauth = store.fetchall("findings_oauth", limit=20)
    return {
        "tenant_count": len(tenants),
        "oauth_grant_count": len(oauth),
        "tenants": tenants,
        "oauth_grants": oauth,
        "inventory": inventory(init_db=False),
    }


@app.post("/api/scan/{tenant}")
async def api_scan(tenant: str) -> dict:
    return _demo_scan(tenant)


@app.get("/api/report/{tenant}")
async def api_report(tenant: str) -> JSONResponse:
    path = REPORTS / f"report_{tenant}.md"
    if not path.exists():
        _demo_scan(tenant)
    if path.exists():
        return JSONResponse({"markdown": path.read_text(encoding="utf-8"), "path": str(path)})
    return JSONResponse({"error": "report not found"}, status_code=404)
