-- SSPM findings schema. Applied on first `sspm audit inventory`.
-- Postgres-compatible; SQLite fallback via store.py.

CREATE TABLE IF NOT EXISTS findings_tenants (
    id SERIAL PRIMARY KEY,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    display_name TEXT,
    settings JSONB NOT NULL DEFAULT '{}',
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_settings (
    id SERIAL PRIMARY KEY,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    setting_value TEXT,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_oauth (
    id SERIAL PRIMARY KEY,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    publisher TEXT,
    scopes TEXT,
    last_used TIMESTAMPTZ,
    risk_level TEXT NOT NULL DEFAULT 'unknown',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_drift (
    id SERIAL PRIMARY KEY,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    first_observed TIMESTAMPTZ,
    last_observed TIMESTAMPTZ,
    change_source TEXT DEFAULT 'unknown',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_compliance (
    id SERIAL PRIMARY KEY,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    control_reference TEXT NOT NULL,
    finding_ref TEXT,
    mapped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    tenant_type TEXT NOT NULL,
    client_id TEXT,
    schedule_cron TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
