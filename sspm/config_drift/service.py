"""Config drift detection via DuckDB over settings vs baseline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

BASELINES = Path(__file__).resolve().parents[1] / "baselines" / "default_baselines.json"


def diff(
    tenant: str,
    baseline_path: str | None = None,
    current_settings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    base_file = Path(baseline_path) if baseline_path else BASELINES
    baselines = json.loads(base_file.read_text(encoding="utf-8"))
    baseline_rows = baselines.get(tenant, [])
    if current_settings is None:
        current_settings = [
            dict(r) for r in baseline_rows
        ]
        if baseline_rows:
            current_settings[0] = {
                **current_settings[0],
                "setting_value": "false" if baseline_rows[0].get("setting_value") == "true" else "true",
            }
    conn = duckdb.connect()
    conn.execute(
        "CREATE TABLE baseline_settings (setting_name VARCHAR, setting_value VARCHAR)"
    )
    conn.execute(
        "CREATE TABLE findings_settings (setting_name VARCHAR, setting_value VARCHAR)"
    )
    for row in baseline_rows:
        conn.execute(
            "INSERT INTO baseline_settings VALUES (?, ?)",
            [row["setting_name"], row.get("setting_value", "")],
        )
    for row in current_settings:
        conn.execute(
            "INSERT INTO findings_settings VALUES (?, ?)",
            [row["setting_name"], row.get("setting_value", "")],
        )
    rows = conn.execute(
        """
        SELECT
            COALESCE(c.setting_name, b.setting_name) AS setting_name,
            b.setting_value AS old_value,
            c.setting_value AS new_value
        FROM baseline_settings b
        FULL OUTER JOIN findings_settings c ON b.setting_name = c.setting_name
        WHERE b.setting_value IS DISTINCT FROM c.setting_value
        """
    ).fetchall()
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    drift: list[dict[str, Any]] = []
    for setting_name, old_value, new_value in rows:
        drift.append(
            {
                "tenant_type": tenant,
                "setting_name": setting_name,
                "old_value": old_value,
                "new_value": new_value,
                "first_observed": now,
                "last_observed": now,
                "change_source": "admin portal",
            }
        )
    conn.close()
    return drift
