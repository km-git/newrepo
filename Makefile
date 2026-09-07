PYTHON ?= $(wildcard .venv/bin/python)
ifeq ($(PYTHON),)
PYTHON := python3
endif
DOMAIN ?= example.com.au
OUT ?= output/dmarc
DSPM_DB ?= output/dspm/dspm.sqlite
export DSPM_DB

.PHONY: dmarc-all dmarc-test dmarc-ui dmarc-inventory \
	dspm-audit-inventory dspm-discover dspm-classify dspm-risk dspm-all dspm-test \
	dspm-improve dspm-gap-audit dspm-watch dspm-monthly

dmarc-inventory:
	$(PYTHON) -m dmarc audit inventory --output-dir $(OUT)

dmarc-all: dmarc-inventory
	$(PYTHON) -m dmarc ingest pull --fixtures --output-dir $(OUT)
	$(PYTHON) -m dmarc dns check --domain $(DOMAIN) --output-dir $(OUT)
	$(PYTHON) -m dmarc spf parse --domain $(DOMAIN) --output-dir $(OUT)
	$(PYTHON) -m dmarc dkim check --domain $(DOMAIN) --output-dir $(OUT)
	$(PYTHON) -m dmarc aggregate report --domain $(DOMAIN) --since 30d --output-dir $(OUT)
	$(PYTHON) -m dmarc forensic list --since 30d --output-dir $(OUT)
	$(PYTHON) -m dmarc inbox test --from-addr noreply@$(DOMAIN) --to seed1@gmail.com,seed2@outlook.com,seed3@yahoo.com --output-dir $(OUT)
	$(PYTHON) -m dmarc report generate --domain $(DOMAIN) --since 30d --output $(OUT)/report.md --output-dir $(OUT) --offline
	$(PYTHON) -m dmarc monthly --output-dir $(OUT) --monthly-dir monthly
	$(PYTHON) -m dmarc ui --static --output-dir $(OUT)

dmarc-ui:
	$(PYTHON) -m dmarc ui --host 0.0.0.0 --port 8765 --output-dir $(OUT)

dmarc-test:
	$(PYTHON) -m pytest tests/dmarc dmarc -q --tb=short

dspm-audit-inventory:
	$(PYTHON) -m dspm audit inventory

dspm-discover:
	$(PYTHON) -m dspm --persist discovery dir $(or $(data),examples/)

dspm-classify:
	$(PYTHON) -m dspm --persist classify $(or $(data),examples/sample.csv)

dspm-risk:
	$(PYTHON) -m dspm --persist risk score --since 7d --fixture examples/risk_fixture.json

dspm-watch:
	$(PYTHON) -m dspm loop watch

dspm-improve:
	$(PYTHON) -m dspm loop improve

dspm-gap-audit:
	$(PYTHON) -m dspm loop gap-audit

dspm-monthly:
	$(PYTHON) -m dspm loop monthly

dspm-all: dspm-audit-inventory dspm-discover dspm-classify dspm-risk
	$(PYTHON) -m dspm exposure scan --fixture examples/prowler_fixture.json
	$(PYTHON) -m dspm access map --store 1
	$(PYTHON) -m dspm encryption-check examples/
	$(PYTHON) -m dspm shadow scan --path examples/
	$(PYTHON) -m dspm custom-types list
	$(PYTHON) -m dspm compliance map --framework gdpr --fixture examples/risk_fixture.json
	$(PYTHON) -m dspm ai-security scan-export examples/prompt_log.jsonl
	$(PYTHON) -m dspm remediate plan --dry-run
	$(PYTHON) -m dspm loop watch
	$(PYTHON) -m dspm loop improve
	$(PYTHON) -m dspm loop monthly

dspm-test:
	$(PYTHON) -m pytest tests/test_dspm_architecture.py tests/test_dspm_core.py tests/test_dspm_loop.py tests/test_dspm_improve.py -q
