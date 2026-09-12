-- Cloud Cost & Configuration Review — seven finding tables.
-- Auto-created on first `cost audit inventory`. SQLite-compatible; Postgres too.

CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    account_id TEXT NOT NULL,
    region TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '{}',
    monthly_cost REAL NOT NULL DEFAULT 0,
    config_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'sandbox',
    scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    account_id TEXT NOT NULL,
    region TEXT NOT NULL,
    service TEXT NOT NULL,
    period TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    tag_key TEXT NOT NULL DEFAULT '',
    tag_value TEXT NOT NULL DEFAULT '',
    scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings_rightsizing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    current_type TEXT NOT NULL,
    recommended_type TEXT NOT NULL,
    monthly_savings_estimate REAL NOT NULL DEFAULT 0,
    risk_level TEXT NOT NULL DEFAULT 'low',
    reason TEXT NOT NULL DEFAULT '',
    scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings_untagged (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    missing_tags TEXT NOT NULL,
    monthly_cost REAL NOT NULL DEFAULT 0,
    scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings_drift (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    field TEXT NOT NULL,
    baseline TEXT NOT NULL,
    current_value TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'config',
    scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings_compliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    control_name TEXT NOT NULL,
    status TEXT NOT NULL,
    observation_ids TEXT NOT NULL DEFAULT '[]',
    scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
