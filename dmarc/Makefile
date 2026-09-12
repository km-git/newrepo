.PHONY: install test lint dmarc-all dmarc-web dmarc-scan

PYTHON ?= python3
DOMAIN ?= example.com.au

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check dmarc/ tests/

dmarc-web:
	$(PYTHON) -m dmarc web serve --port 8767

dmarc-audit-inventory:
	$(PYTHON) -m dmarc audit inventory

dmarc-dns:
	$(PYTHON) -m dmarc dns check --domain $(DOMAIN)

dmarc-spf:
	$(PYTHON) -m dmarc spf parse --domain $(DOMAIN)

dmarc-dkim:
	$(PYTHON) -m dmarc dkim check --domain $(DOMAIN) --all-selectors

dmarc-ingest:
	$(PYTHON) -m dmarc ingest pull --domain $(DOMAIN) --demo

dmarc-aggregate:
	$(PYTHON) -m dmarc aggregate report --since 30d

dmarc-forensic:
	$(PYTHON) -m dmarc forensic list --domain $(DOMAIN) --demo

dmarc-inbox:
	$(PYTHON) -m dmarc inbox test --from noreply@$(DOMAIN) --to seed1@gmail.com,seed2@outlook.com

dmarc-report:
	$(PYTHON) -m dmarc report generate --domain $(DOMAIN) --since 30d

dmarc-scan:
	$(PYTHON) -m dmarc scan --domain $(DOMAIN)

dmarc-all: install dmarc-audit-inventory dmarc-dns dmarc-spf dmarc-dkim dmarc-ingest dmarc-aggregate dmarc-forensic dmarc-inbox dmarc-report
	@echo "dmarc-all complete for $(DOMAIN)"
