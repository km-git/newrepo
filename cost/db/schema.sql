-- Cloud Cost & Configuration Review schema.
-- Applied on first `cost audit inventory`. SQLite default; Postgres-compatible types.

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    account_ref TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    provider TEXT NOT NULL,
    region TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '{}',
    monthly_cost REAL NOT NULL DEFAULT 0,
    extra TEXT NOT NULL DEFAULT '{}',
    discovered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    provider TEXT NOT NULL,
    service TEXT NOT NULL,
    region TEXT NOT NULL,
    tag_key TEXT,
    tag_value TEXT,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_rightsizing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    current_type TEXT NOT NULL,
    recommended_type TEXT NOT NULL,
    monthly_savings_estimate REAL NOT NULL,
    risk_level TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    scanned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_untagged (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    missing_tags TEXT NOT NULL DEFAULT '[]',
    monthly_cost REAL NOT NULL DEFAULT 0,
    extra TEXT NOT NULL DEFAULT '{}',
    scanned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_drift (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    field TEXT NOT NULL,
    baseline_value TEXT NOT NULL,
    current_value TEXT NOT NULL,
    cost_impact REAL NOT NULL DEFAULT 0,
    extra TEXT NOT NULL DEFAULT '{}',
    detected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_compliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    finding_ref TEXT NOT NULL,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    mapping_status TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    mapped_at TEXT NOT NULL
);
