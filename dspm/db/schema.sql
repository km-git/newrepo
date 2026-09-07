-- DSPM findings schema. Applied on first `dspm audit inventory`.
-- SQLite by default; Postgres-compatible types used where they overlap.

CREATE TABLE IF NOT EXISTS findings_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    kind TEXT NOT NULL,
    location TEXT NOT NULL,
    name TEXT,
    managed INTEGER NOT NULL DEFAULT 1,
    extra TEXT NOT NULL DEFAULT '{}',
    discovered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    location TEXT NOT NULL,
    type TEXT NOT NULL,
    confidence REAL NOT NULL,
    verdict TEXT NOT NULL,
    suggested_action TEXT NOT NULL DEFAULT '',
    extra TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_risk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    vector TEXT NOT NULL,
    suggested_action TEXT NOT NULL DEFAULT '',
    scored_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER,
    principal TEXT NOT NULL,
    principal_type TEXT NOT NULL,
    permission TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_exposure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER,
    check_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    public INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_encryption (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    at_rest INTEGER NOT NULL DEFAULT 0,
    in_flight INTEGER NOT NULL DEFAULT 0,
    scanner TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_shadow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    kind TEXT NOT NULL,
    reason TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_compliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    status TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    mapped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings_ai_security (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store TEXT NOT NULL,
    location TEXT NOT NULL,
    type TEXT NOT NULL,
    confidence REAL NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}',
    scanned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS remediation_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    action TEXT NOT NULL,
    policy TEXT NOT NULL,
    preconditions TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL,
    dry_run_safe INTEGER NOT NULL DEFAULT 1,
    extra TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
