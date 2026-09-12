-- Postgres schema (docker-compose). SQLite auto-creates the same six tables.
CREATE TABLE IF NOT EXISTS findings_dns (
  id SERIAL PRIMARY KEY,
  domain TEXT NOT NULL,
  record_type TEXT NOT NULL,
  value TEXT,
  ttl INTEGER,
  last_checked_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_spf (
  id SERIAL PRIMARY KEY,
  domain TEXT NOT NULL,
  record TEXT,
  dns_lookup_count INTEGER,
  lookups TEXT,
  all_qualifier TEXT,
  warnings TEXT,
  last_checked_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_dkim (
  id SERIAL PRIMARY KEY,
  domain TEXT NOT NULL,
  selector TEXT,
  record TEXT,
  public_key_length INTEGER,
  warnings TEXT,
  last_checked_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_dmarc (
  id SERIAL PRIMARY KEY,
  domain TEXT NOT NULL,
  source_org TEXT,
  source_ip TEXT,
  count INTEGER,
  disposition TEXT,
  dkim_result TEXT,
  spf_result TEXT,
  date_range TEXT,
  received_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_forensic (
  id SERIAL PRIMARY KEY,
  domain TEXT NOT NULL,
  source_ip TEXT,
  from_address TEXT,
  subject TEXT,
  dkim_result TEXT,
  spf_result TEXT,
  received_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_inbox (
  id SERIAL PRIMARY KEY,
  provider TEXT,
  seed_account TEXT,
  placement TEXT,
  subject TEXT,
  from_address TEXT,
  sent_at TIMESTAMPTZ NOT NULL
);
