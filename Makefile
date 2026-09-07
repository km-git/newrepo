.PHONY: cost-all cost-ui cost-test cost-ruff

PYTHON ?= .venv/bin/python

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
