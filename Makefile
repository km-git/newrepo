.PHONY: dmarc-all dmarc-test dmarc-ui dmarc-inventory \
	sspm-audit-inventory sspm-all sspm-test sspm-watch sspm-monthly sspm-web-static sspm-demo \
	dspm-audit-inventory dspm-discover dspm-classify dspm-risk dspm-all dspm-test dspm-improve \
	dspm-gap-audit dspm-watch dspm-monthly

PYTHON ?= $(wildcard .venv/bin/python)
ifeq ($(PYTHON),)
PYTHON := python3
endif
DOMAIN ?= example.com.au
OUT ?= output/dmarc
SSPM_DB ?= output/sspm/sspm.sqlite
DSPM_DB ?= output/dspm/dspm.sqlite
export SSPM_DB
export DSPM_DB

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

sspm-audit-inventory:
	$(PYTHON) -m sspm audit inventory

sspm-watch:
	$(PYTHON) -m sspm loop watch

sspm-monthly:
	$(PYTHON) -m sspm loop monthly

sspm-web-static:
	$(PYTHON) -m sspm web --static

sspm-demo:
	$(PYTHON) -m sspm --persist demo

sspm-all: sspm-audit-inventory
	$(PYTHON) -m sspm --persist discovery m365
	$(PYTHON) -m sspm --persist discovery gws
	$(PYTHON) -m sspm --persist discovery github
	$(PYTHON) -m sspm --persist discovery slack
	$(PYTHON) -m sspm --persist discovery okta
	$(PYTHON) -m sspm --persist oauth-grants list --tenant all
	$(PYTHON) -m sspm --persist drift diff --tenant m365
	$(PYTHON) -m sspm --persist compliance map --framework cis-m365 --tenant m365
	$(PYTHON) -m sspm report generate --tenant m365 --output output/sspm/report.md
	$(PYTHON) -m sspm tenant add --name demo-m365 --type m365 --client-id demo || true
	$(PYTHON) -m sspm tenant list
	$(PYTHON) -m sspm disclaimers show --name disclaimer_au
	$(PYTHON) -m sspm loop watch
	$(PYTHON) -m sspm loop monthly
	$(PYTHON) -m sspm web --static
	$(PYTHON) -m sspm --persist demo

sspm-test:
	$(PYTHON) -m pytest tests/test_sspm_architecture.py tests/test_sspm_core.py tests/test_sspm_loop.py tests/test_sspm_web.py tests/test_sspm_report.py -q

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

.PHONY: cost-all cost-ui cost-test cost-ruff

cost-all:
	$(PYTHON) -m cost scan-all --sandbox
	$(PYTHON) -m cost ui --static

cost-ui:
	$(PYTHON) -m cost ui --host 0.0.0.0 --port 8765

cost-test:
	$(PYTHON) -m pytest tests/test_cost_pipeline.py tests/test_cost_webui.py tests/test_cost_language.py tests/test_cost_workflows.py -q --tb=short

cost-ruff:
	ruff check --config ruff.toml cost/ tests/test_cost_pipeline.py tests/test_cost_webui.py tests/test_cost_language.py tests/test_cost_workflows.py
	ruff format --check cost/ tests/test_cost_pipeline.py tests/test_cost_webui.py tests/test_cost_language.py tests/test_cost_workflows.py
