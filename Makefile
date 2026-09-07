.PHONY: dspm-audit-inventory dspm-discover dspm-classify dspm-risk dspm-all dspm-test

PYTHON ?= python3
DSPM_DB ?= output/dspm/dspm.sqlite
export DSPM_DB

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
	$(PYTHON) -m dspm loop monthly

dspm-test:
	$(PYTHON) -m pytest tests/test_dspm_architecture.py tests/test_dspm_core.py tests/test_dspm_loop.py -q
