PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
INPUT ?= data/cameo-database.ods
OUTPUT_DIR ?= dist
RELEASE_TAG ?=

.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(VENV_PYTHON): pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"
	@touch $(VENV_PYTHON)

install: $(VENV_PYTHON) ## Create .venv and install package + dev deps

test: $(VENV_PYTHON) ## Run the pytest suite
	$(VENV)/bin/pytest

run: $(VENV_PYTHON) ## Generate all 28 files in $(OUTPUT_DIR)/ (override INPUT, OUTPUT_DIR, RELEASE_TAG)
	$(VENV_PYTHON) -m cameo_convert --input $(INPUT) --output-dir $(OUTPUT_DIR) --release-tag "$(RELEASE_TAG)"

quick: $(VENV_PYTHON) ## Fast iteration: clean variant, json+csv+md+sqlite only, no bundles
	$(VENV_PYTHON) -m cameo_convert --input $(INPUT) --output-dir $(OUTPUT_DIR) --variants clean --formats json,csv,md,sqlite --bundle ''

smoke: $(VENV_PYTHON) ## Mirror the CI smoke test (writes to /tmp/dist)
	$(VENV_PYTHON) -m cameo_convert --input $(INPUT) --output-dir /tmp/dist --variants clean --formats json,csv,sqlite --bundle ''
	@ls -la /tmp/dist

verify: $(VENV_PYTHON) ## Clean + run + assert expected file count + spot-check §6.4 example
	rm -rf $(OUTPUT_DIR)
	$(VENV_PYTHON) -m cameo_convert --input $(INPUT) --output-dir $(OUTPUT_DIR) --release-tag "$(RELEASE_TAG)"
	@count=$$(ls $(OUTPUT_DIR) | wc -l | tr -d ' '); \
		echo "files in $(OUTPUT_DIR)/: $$count (expected 28)"; \
		[ "$$count" = "28" ] || (echo "FAIL: file count mismatch"; exit 1)
	@$(VENV_PYTHON) -c "import json, sys; \
		d = json.load(open('$(OUTPUT_DIR)/cameo-convert-cards-clean.json' if not '$(RELEASE_TAG)' else '$(OUTPUT_DIR)/cameo-convert-$(RELEASE_TAG)-cards-clean.json')); \
		c = d['cards'].get('Aquapolis|Town Volunteers|136'); \
		sys.exit(0 if c and any(x['subject']=='Bulbasaur' for x in c['cameos']) else 1)" \
		&& echo "spot-check: Bulbasaur on Aquapolis|Town Volunteers|136 — OK" \
		|| (echo "FAIL: §6.4 spot-check missing Bulbasaur"; exit 1)

goldens: $(VENV_PYTHON) ## Regenerate tests/goldens/*.json from the current source
	$(VENV)/bin/pytest tests/test_goldens.py --regen-goldens -q

fixture: $(VENV_PYTHON) ## Rebuild tests/fixtures/tiny_sample.ods
	$(VENV_PYTHON) tests/fixtures/build_tiny_sample.py

shell: $(VENV_PYTHON) ## Drop into a Python REPL with the package importable
	$(VENV_PYTHON)

clean: ## Remove generated outputs and Python caches
	rm -rf $(OUTPUT_DIR) build dist src/*.egg-info *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

distclean: clean ## Also remove the virtualenv
	rm -rf $(VENV)

.PHONY: help install test run quick smoke verify goldens fixture shell clean distclean
