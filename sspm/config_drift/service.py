"""Config drift vs shipped baselines. DuckDB when installed; SQLite otherwise."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sspm.config_drift.models import DriftFinding
from sspm.db.store import FindingsStore, utcnow
from sspm.discovery import load_fixture
from sspm.paths import load_baseline_map


def load_baseline(tenant_type: str, path: Path | None = None) -> dict[str, str]:
    if path is None:
        return load_baseline_map(tenant_type)
    name = Path(path).name
    if name == "m365.json":
        return load_baseline_map("m365")
    if name == "gws.json":
        return load_baseline_map("gws")
    if name == "github.json":
        return load_baseline_map("github")
    if name == "slack.json":
        return load_baseline_map("slack")
    if name == "okta.json":
        return load_baseline_map("okta")
    raise ValueError("baseline must be a shipped tenant filename")


def _diff_maps(
    current: dict[str, str],
    baseline: dict[str, str],
    *,
    tenant_name: str,
    tenant_type: str,
    now: str,
) -> list[DriftFinding]:
    findings: list[DriftFinding] = []
    keys = sorted(set(current) | set(baseline))
    for key in keys:
        old = baseline.get(key)
        new = current.get(key)
        if old == new:
            continue
        findings.append(
            DriftFinding(
                tenant_name=tenant_name,
                tenant_type=tenant_type,
                setting_name=key,
                old_value=old,
                new_value=new,
                first_observed=now,
                last_observed=now,
                change_source="unknown",
            )
        )
    return findings


def diff_tenant(
    *,
    tenant: str = "m365",
    tenant_name: str | None = None,
    baseline: Path | None = None,
    current: dict[str, Any] | None = None,
    store: FindingsStore | None = None,
) -> list[DriftFinding]:
    name = tenant_name or f"{tenant}-demo"
    snap = current or load_fixture(tenant)
    current_map = {str(s["name"]): str(s.get("value")) for s in snap.get("settings") or []}
    baseline_map = load_baseline(tenant, baseline)
    now = utcnow()
    try:
        findings = _duckdb_diff(current_map, baseline_map, tenant_name=name, tenant_type=tenant, now=now)
    except Exception:
        findings = _diff_maps(current_map, baseline_map, tenant_name=name, tenant_type=tenant, now=now)
    if store is not None:
        for item in findings:
            store.insert("findings_drift", {**item.model_dump(), "extra": {}, "observed_at": now})
    return findings


def _duckdb_diff(
    current: dict[str, str],
    baseline: dict[str, str],
    *,
    tenant_name: str,
    tenant_type: str,
    now: str,
) -> list[DriftFinding]:
    import duckdb

    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE current_settings (setting_name VARCHAR, setting_value VARCHAR)")
    con.execute("CREATE TABLE baseline_settings (setting_name VARCHAR, setting_value VARCHAR)")
    con.executemany("INSERT INTO current_settings VALUES (?, ?)", list(current.items()))
    con.executemany("INSERT INTO baseline_settings VALUES (?, ?)", list(baseline.items()))
    rows = con.execute(
        """
        SELECT
          COALESCE(c.setting_name, b.setting_name) AS setting_name,
          b.setting_value AS old_value,
          c.setting_value AS new_value
        FROM current_settings c
        FULL OUTER JOIN baseline_settings b USING (setting_name)
        WHERE COALESCE(c.setting_value, '') <> COALESCE(b.setting_value, '')
        ORDER BY setting_name
        """
    ).fetchall()
    return [
        DriftFinding(
            tenant_name=tenant_name,
            tenant_type=tenant_type,
            setting_name=row[0],
            old_value=row[1],
            new_value=row[2],
            first_observed=now,
            last_observed=now,
            change_source="unknown",
        )
        for row in rows
    ]
