.PHONY: install test lint sspm-all sspm-web sspm-test

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

install:
	$(PIP) install -e ".[dev]"

sspm-audit-inventory:
	$(PYTHON) -m sspm audit inventory

sspm-discover-m365:
	$(PYTHON) -m sspm discovery m365 --tenant-id contoso.onmicrosoft.com

sspm-discover-gws:
	$(PYTHON) -m sspm discovery gws --domain example.com

sspm-discover-github:
	$(PYTHON) -m sspm discovery github --org example-org

sspm-discover-slack:
	$(PYTHON) -m sspm discovery slack --workspace example-workspace

sspm-discover-okta:
	$(PYTHON) -m sspm discovery okta --org example.okta.com

sspm-oauth:
	$(PYTHON) -m sspm oauth-grants list --tenant m365

sspm-drift:
	$(PYTHON) -m sspm drift diff --tenant m365

sspm-compliance:
	$(PYTHON) -m sspm compliance map --framework cis-m365 --tenant m365

sspm-report:
	$(PYTHON) -m sspm report generate --tenant m365 --output output/sspm/report.md

sspm-tenant:
	$(PYTHON) -m sspm tenant add --name demo --type m365 --client-id demo-client
	$(PYTHON) -m sspm tenant list

sspm-disclaimers:
	$(PYTHON) -m sspm disclaimers show --name disclaimer_au

sspm-watch:
	$(PYTHON) -m sspm loop watch

sspm-monthly:
	$(PYTHON) -m sspm loop monthly

sspm-improve:
	$(PYTHON) -m sspm loop improve

sspm-all: sspm-audit-inventory sspm-discover-m365 sspm-discover-gws sspm-discover-github sspm-discover-slack sspm-discover-okta sspm-oauth sspm-drift sspm-compliance sspm-report sspm-tenant sspm-disclaimers sspm-watch sspm-monthly
	@echo "SSPM all modules completed."

sspm-web:
	$(PYTHON) -m sspm web serve --host 0.0.0.0 --port 8766

sspm-test:
	$(PYTHON) -m pytest tests/test_sspm.py sspm -q --tb=short

lint:
	ruff check sspm tests/test_sspm.py

test: sspm-test
