.PHONY: sspm-audit-inventory sspm-all sspm-test sspm-watch sspm-monthly sspm-web-static sspm-demo

PYTHON ?= python3
SSPM_DB ?= output/sspm/sspm.sqlite
export SSPM_DB

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
