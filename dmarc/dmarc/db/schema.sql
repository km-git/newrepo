-- Seeded schema for DMARC findings (also loaded into Postgres via docker-compose)

CREATE TABLE IF NOT EXISTS findings_dns (
    id SERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    record_type TEXT NOT NULL,
    value TEXT NOT NULL,
    ttl INTEGER,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_spf (
    id SERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    record TEXT NOT NULL,
    dns_lookup_count INTEGER NOT NULL,
    lookups JSONB NOT NULL DEFAULT '[]',
    all_qualifier TEXT NOT NULL DEFAULT '?',
    warnings JSONB NOT NULL DEFAULT '[]',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_dkim (
    id SERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    selector TEXT NOT NULL,
    record TEXT NOT NULL,
    public_key_length INTEGER,
    warnings JSONB NOT NULL DEFAULT '[]',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_dmarc (
    id SERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    source_org TEXT NOT NULL,
    source_ip TEXT NOT NULL,
    count INTEGER NOT NULL,
    disposition TEXT NOT NULL,
    dkim_result TEXT NOT NULL,
    spf_result TEXT NOT NULL,
    date_range TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_forensic (
    id SERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    source_ip TEXT NOT NULL,
    from_address TEXT NOT NULL,
    subject TEXT NOT NULL,
    dkim_result TEXT NOT NULL,
    spf_result TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings_inbox (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    seed_account TEXT NOT NULL,
    placement TEXT NOT NULL,
    subject TEXT NOT NULL,
    from_address TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_findings_dns_domain ON findings_dns(domain);
CREATE INDEX IF NOT EXISTS idx_findings_dmarc_domain ON findings_dmarc(domain);
