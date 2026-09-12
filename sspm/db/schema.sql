-- SSPM findings schema. Applied on first `sspm audit inventory`.
-- SQLite by default; Postgres-compatible types used where they overlap.

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    tenant_type TEXT NOT NULL,
    client_id TEXT,
    cron_expr TEXT NOT NULL DEFAULT '0 9 * * 1',
    timezone TEXT NOT NULL DEFAULT 'Australia/Sydney',
    extra TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_name TEXT NOT NULL,
    tenant_type TEXT NOT NULL,
    external_id TEXT,
    display_name TEXT,
    scanner TEXT NOT NULL DEFAULT 'fixture',
    setting_count INTEGER NOT NULL DEFAULT 0,
    extra TEXT NOT NULL DEFAULT '{}',
    discovered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_name TEXT NOT NULL,
    tenant_type TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    extra TEXT NOT NULL DEFAULT '{}',
    observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_oauth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_name TEXT NOT NULL,
    tenant_type TEXT NOT NULL,
    app_name TEXT NOT NULL,
    publisher TEXT,
    scopes TEXT NOT NULL DEFAULT '',
    last_used TEXT,
    risk_level TEXT NOT NULL DEFAULT 'low',
    extra TEXT NOT NULL DEFAULT '{}',
    observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_drift (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_name TEXT NOT NULL,
    tenant_type TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    first_observed TEXT NOT NULL,
    last_observed TEXT NOT NULL,
    change_source TEXT NOT NULL DEFAULT 'unknown',
    extra TEXT NOT NULL DEFAULT '{}',
    observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_compliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_name TEXT NOT NULL,
    tenant_type TEXT NOT NULL,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    title TEXT NOT NULL,
    reference_status TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    mapped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS baseline_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_type TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}'
);
