.PHONY: install test lint dspm-audit-inventory dspm-discover dspm-classify dspm-risk dspm-all

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check dspm/ tests/

dspm-audit-inventory:
	$(PYTHON) -m dspm audit inventory

dspm-discover:
	$(PYTHON) -m dspm discovery dir examples/

dspm-classify:
	$(PYTHON) -m dspm classify run examples/sample.csv

dspm-risk:
	$(PYTHON) -m dspm risk score --data examples/sample.csv --since 7d

dspm-all: dspm-audit-inventory dspm-discover dspm-classify dspm-risk
	$(PYTHON) -m dspm exposure scan
	$(PYTHON) -m dspm access map --store 42
	$(PYTHON) -m dspm shadow scan
	$(PYTHON) -m dspm remediate plan --dry-run
