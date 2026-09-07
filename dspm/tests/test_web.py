"""Web API tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from dspm.web.app import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_dashboard():
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data


def test_index_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "DSPM" in r.text


def test_warehouse_query():
    r = client.post("/api/warehouse/query", json={"sql": "SELECT 1 AS n"})
    assert r.status_code == 200
    assert r.json()["rows"][0]["n"] == 1


def test_governance_mask_api():
    r = client.post("/api/governance/mask", json={"value": "secret", "data_type": "PII"})
    assert r.status_code == 200
    assert "masked" in r.json()


def test_sources_schemes_api():
    r = client.get("/api/sources/schemes")
    assert r.status_code == 200
    assert "s3" in r.json()["schemes"]


def test_sources_scan_api():
    root = Path(__file__).resolve().parents[1]
    r = client.post("/api/sources/scan", json={"uri": f"s3://test-bucket/", "max_objects": 10})
    assert r.status_code == 200
    assert r.json()["object_count"] >= 1
