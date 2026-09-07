.PHONY: licensespend-audit-inventory licensespend-all licensespend-test

PYTHON ?= python3

licensespend-audit-inventory:
	$(PYTHON) -m licensespend audit inventory

licensespend-all:
	$(PYTHON) -m licensespend audit inventory
	$(PYTHON) -m licensespend usage unused --idle-days 90 --fixture examples/ --as-of 2026-09-07
	$(PYTHON) -m licensespend renewals upcoming --days 60 --as-of 2026-09-07
	$(PYTHON) -m licensespend report build --client fixture --out reports/ --as-of 2026-09-07
	$(PYTHON) -m licensespend report build --client northwind --out reports/licensespend --as-of 2026-09-07
	$(PYTHON) -m licensespend ui --static --out reports/

licensespend-test:
	$(PYTHON) -m pytest tests/test_licensespend_architecture.py tests/test_licensespend_core.py tests/test_licensespend_ui.py licensespend -q
