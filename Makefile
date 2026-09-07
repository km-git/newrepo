PYTHON ?= $(wildcard .venv/bin/python)
ifeq ($(PYTHON),)
PYTHON := python3
endif
DOMAIN ?= example.com.au
OUT ?= output/dmarc

.PHONY: dmarc-all dmarc-test dmarc-ui dmarc-inventory

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
