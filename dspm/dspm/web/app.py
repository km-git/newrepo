"""FastAPI web application for DSPM platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from dspm.catalog.service import build_lineage_graph, register_asset, sync_from_discovery
from dspm.classification.service import classify_csv, findings_to_dict
from dspm.discovery.service import discover_directory, stores_to_dict
from dspm.exposure.service import scan_exposure
from dspm.governance.service import apply_mask, list_policies, seed_policies
from dspm.integrations.github import scan_repo
from dspm.models import Finding
from dspm.observability.service import dashboard_summary, evaluate_alerts, seed_alert_rules
from dspm.remediation.service import build_plan
from dspm.risk.service import risks_to_dict, score_findings
from dspm.siem.service import correlate_findings, search_events
from dspm.sources.registry import SUPPORTED_SCHEMES, discover, preview, scan_and_classify
from dspm.sources.persist import save_source_scan
from dspm.store.db import fetch_all, init_db, persist_scan_results
from dspm.warehouse.service import execute_sql, query_history

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "sample.csv"


class SqlRequest(BaseModel):
    sql: str
    user: str = "webui"


class MaskRequest(BaseModel):
    value: str
    data_type: str = "PII"
    role: str = "DATA_USER"


class SiemSearchRequest(BaseModel):
    query: str = "*"


class SourceScanRequest(BaseModel):
    uri: str
    max_objects: int = 200


def _run_full_scan() -> dict:
    init_db()
    findings = findings_to_dict(classify_csv(EXAMPLES, max_rows=50))
    exposures = scan_exposure("aws")
    risks = risks_to_dict(score_findings([Finding(**f) for f in findings[:20]], exposures))
    persist_scan_results(findings, risks, exposures)
    summary = dashboard_summary(findings, risks, exposures)
    correlate_findings(findings, exposures)
    sync_from_discovery(stores_to_dict(discover_directory(EXAMPLES.parent)))
    seed_policies()
    seed_alert_rules()
    return {"findings": findings, "risks": risks, "exposures": exposures, "summary": summary}


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    if not fetch_all("findings", limit=1):
        _run_full_scan()
    yield


app = FastAPI(
    title="DSPM Platform",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "dspm-web", "version": "0.2.0"}


@app.get("/api/dashboard")
async def api_dashboard() -> dict:
    findings = fetch_all("findings", limit=100)
    risks = fetch_all("risk_scores", limit=100)
    exposures = fetch_all("exposures", limit=50)
    if not findings:
        return _run_full_scan()
    summary = dashboard_summary(findings, [{"score": r["score"]} for r in risks], exposures)
    return {
        "summary": summary,
        "alerts": evaluate_alerts(summary),
        "recent_findings": findings[:10],
        "recent_risks": risks[:10],
        "recent_exposures": exposures[:5],
    }


@app.post("/api/scan")
async def api_scan() -> dict:
    return _run_full_scan()


@app.get("/api/findings")
async def api_findings(limit: int = 50) -> list:
    return fetch_all("findings", limit=limit)


@app.get("/api/risks")
async def api_risks(limit: int = 50) -> list:
    return fetch_all("risk_scores", limit=limit)


@app.get("/api/exposures")
async def api_exposures(limit: int = 50) -> list:
    return fetch_all("exposures", limit=50)


@app.get("/api/catalog")
async def api_catalog() -> dict:
    return {"assets": fetch_all("catalog_assets", limit=100), "lineage": build_lineage_graph()}


@app.post("/api/catalog/register")
async def api_catalog_register(name: str, asset_type: str = "table") -> dict:
    return register_asset(name, asset_type)


@app.get("/api/governance")
async def api_governance() -> list:
    return list_policies()


@app.post("/api/governance/mask")
async def api_mask(body: MaskRequest) -> dict:
    return {"masked": apply_mask(body.value, body.data_type, body.role)}


@app.get("/api/siem")
async def api_siem(q: str = "*") -> list:
    return search_events(q)


@app.post("/api/siem/search")
async def api_siem_search(body: SiemSearchRequest) -> list:
    return search_events(body.query)


@app.get("/api/observability")
async def api_observability() -> dict:
    metrics = fetch_all("observability_metrics", limit=50)
    return {"metrics": metrics, "alert_rules": seed_alert_rules()}


@app.post("/api/warehouse/query")
async def api_warehouse_query(body: SqlRequest) -> dict:
    try:
        return execute_sql(body.sql, user=body.user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/warehouse/history")
async def api_warehouse_history() -> list:
    return query_history()


@app.get("/api/remediation")
async def api_remediation() -> list:
    return build_plan(dry_run=True)


@app.get("/api/github/scan/{owner}/{repo}")
async def api_github_scan(owner: str, repo: str) -> dict:
    return scan_repo(owner, repo)


@app.get("/api/sources/schemes")
async def api_source_schemes() -> dict:
    return {"schemes": SUPPORTED_SCHEMES}


@app.get("/api/sources/objects")
async def api_source_objects(limit: int = 100) -> list:
    return fetch_all("source_objects", limit=limit)


@app.get("/api/sources/scans")
async def api_source_scans(limit: int = 20) -> list:
    return fetch_all("source_scans", limit=limit)


@app.post("/api/sources/discover")
async def api_sources_discover(body: SourceScanRequest) -> dict:
    objects = discover(body.uri, max_objects=body.max_objects)
    return {"uri": body.uri, "count": len(objects), "objects": [o.model_dump() for o in objects[:50]]}


@app.post("/api/sources/scan")
async def api_sources_scan(body: SourceScanRequest) -> dict:
    result = scan_and_classify(body.uri, max_objects=body.max_objects)
    saved = save_source_scan(result)
    return {
        "source_uri": result.source_uri,
        "provider": result.provider,
        "object_count": result.object_count,
        "finding_count": len(result.findings),
        "saved": saved,
        "findings": result.findings[:30],
        "objects": [o.model_dump() for o in result.objects[:20]],
    }


@app.get("/api/sources/preview")
async def api_sources_preview(uri: str, path: str = "") -> dict:
    return preview(uri, path).model_dump()


def create_app() -> FastAPI:
    return app
