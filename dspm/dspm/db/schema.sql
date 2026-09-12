-- DSPM findings schema (auto-created on first audit inventory run)

CREATE TABLE IF NOT EXISTS findings_stores (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    location TEXT NOT NULL,
    provider TEXT,
    store_type TEXT,
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    location TEXT NOT NULL,
    type TEXT NOT NULL,
    confidence REAL NOT NULL,
    verdict TEXT NOT NULL,
    suggested_action TEXT,
    classified_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_risk (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER REFERENCES findings(id),
    score REAL NOT NULL,
    vector TEXT,
    suggested_action TEXT,
    scored_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_access (
    id SERIAL PRIMARY KEY,
    principal TEXT NOT NULL,
    store_id INTEGER REFERENCES findings_stores(id),
    permission TEXT NOT NULL,
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_exposure (
    id SERIAL PRIMARY KEY,
    resource TEXT NOT NULL,
    exposure_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    details JSONB,
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_encryption (
    id SERIAL PRIMARY KEY,
    resource TEXT NOT NULL,
    encrypted BOOLEAN NOT NULL,
    encryption_type TEXT,
    details JSONB,
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_shadow (
    id SERIAL PRIMARY KEY,
    resource TEXT NOT NULL,
    shadow_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    details JSONB,
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_compliance (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER REFERENCES findings(id),
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    status TEXT NOT NULL,
    mapped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_ai_security (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    prompt_excerpt TEXT,
    finding_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    scanned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS remediation_plan (
    id SERIAL PRIMARY KEY,
    target TEXT NOT NULL,
    action TEXT NOT NULL,
    preconditions JSONB,
    risk_level TEXT NOT NULL,
    dry_run_safe BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
