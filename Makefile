# LiteLLM Makefile
# Simple Makefile for running tests and basic development tasks

.PHONY: help test test-unit test-unit-llms test-unit-proxy-guardrails test-unit-proxy-core test-unit-proxy-misc \
	test-unit-integrations test-unit-core-utils test-unit-other test-unit-root \
	test-proxy-unit-a test-proxy-unit-b test-integration test-unit-helm \
	info lint lint-dev format \
	install-dev install-proxy-dev install-test-deps \
	install-helm-unittest check-circular-imports check-import-safety
.PHONY: install-dev-uv install-proxy-dev-uv install-test-deps-uv format-uv format-check-uv lint-uv lint-ruff-uv lint-mypy-uv lint-black-uv check-circular-imports-uv check-import-safety-uv test-uv test-unit-uv test-integration-uv
.PHONY: lint-format-changed-uv lint-ruff-dev-uv lint-ruff-FULL-dev-uv lint-dev-uv
.PHONY: test-unit-llms-uv test-unit-proxy-guardrails-uv test-unit-proxy-core-uv test-unit-proxy-misc-uv test-unit-integrations-uv test-unit-core-utils-uv test-unit-other-uv test-unit-root-uv
.PHONY: test-proxy-unit-a-uv test-proxy-unit-b-uv test-llm-translation-uv test-llm-translation-single-uv
.PHONY: sync-deps sync-deps-check sync-deps-dry-run

# Virtual environment activation helper
VENV_ACTIVATE = . .venv/bin/activate &&

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "=== Poetry-based (original) ==="
	@echo "  make install-dev        - Install development dependencies"
	@echo "  make install-proxy-dev  - Install proxy development dependencies"
	@echo "  make install-dev-ci     - Install dev dependencies (CI-compatible, pins OpenAI)"
	@echo "  make install-proxy-dev-ci - Install proxy dev dependencies (CI-compatible)"
	@echo "  make install-test-deps  - Install test dependencies"
	@echo "  make format             - Apply Black code formatting"
	@echo "  make format-check       - Check Black code formatting (matches CI)"
	@echo "  make lint               - Run all linting"
	@echo "  make lint-ruff          - Run Ruff linting only"
	@echo "  make lint-mypy          - Run MyPy type checking only"
	@echo "  make lint-black         - Check Black formatting (matches CI)"
	@echo "  make check-circular-imports - Check for circular imports"
	@echo "  make check-import-safety - Check import safety"
	@echo "  make test               - Run all tests"
	@echo "  make test-unit          - Run unit tests (tests/test_litellm)"
	@echo "  make test-unit-llms     - Run LLM provider tests (~225 files)"
	@echo "  make test-unit-proxy-guardrails - Run proxy guardrails+mgmt tests (~51 files)"
	@echo "  make test-unit-proxy-core - Run proxy auth+client+db+hooks tests (~52 files)"
	@echo "  make test-unit-proxy-misc - Run proxy misc tests (~77 files)"
	@echo "  make test-unit-integrations - Run integration tests (~60 files)"
	@echo "  make test-unit-core-utils - Run core utils tests (~32 files)"
	@echo "  make test-unit-other    - Run other tests (caching, responses, etc., ~69 files)"
	@echo "  make test-unit-root     - Run root-level tests (~34 files)"
	@echo "  make test-proxy-unit-a  - Run proxy_unit_tests (a-o, ~20 files)"
	@echo "  make test-proxy-unit-b  - Run proxy_unit_tests (p-z, ~28 files)"
	@echo "  make test-integration   - Run integration tests"
	@echo ""
	@echo "=== UV-based (PEP-621) ==="
	@echo "  make install-dev-uv     - Install dev dependencies with uv"
	@echo "  make install-proxy-dev-uv - Install proxy dev dependencies with uv"
	@echo "  make install-test-deps-uv - Install test dependencies with uv"
	@echo "  make format-uv          - Apply Black code formatting (uv)"
	@echo "  make format-check-uv    - Check Black code formatting (uv)"
	@echo "  make lint-uv            - Run all linting (uv)"
	@echo "  make lint-dev-uv        - Faster linting for local dev (uv)"
	@echo "  make lint-ruff-uv       - Run Ruff linting only (uv)"
	@echo "  make lint-mypy-uv       - Run MyPy type checking only (uv)"
	@echo "  make lint-format-changed-uv - Format only changed lines (uv)"
	@echo "  make lint-ruff-dev-uv   - Ruff diff-quality check (uv)"
	@echo "  make lint-ruff-FULL-dev-uv - Ruff check on changed files (uv)"
	@echo "  make check-circular-imports-uv - Check for circular imports (uv)"
	@echo "  make check-import-safety-uv - Check import safety (uv)"
	@echo "  make test-uv            - Run all tests (uv)"
	@echo "  make test-unit-uv       - Run unit tests (uv)"
	@echo "  make test-unit-llms-uv  - Run LLM provider tests (uv)"
	@echo "  make test-unit-proxy-guardrails-uv - Run proxy guardrails+mgmt tests (uv)"
	@echo "  make test-unit-proxy-core-uv - Run proxy auth+client+db+hooks tests (uv)"
	@echo "  make test-unit-proxy-misc-uv - Run proxy misc tests (uv)"
	@echo "  make test-unit-integrations-uv - Run integration tests (uv)"
	@echo "  make test-unit-core-utils-uv - Run core utils tests (uv)"
	@echo "  make test-unit-other-uv - Run other tests (uv)"
	@echo "  make test-unit-root-uv  - Run root-level tests (uv)"
	@echo "  make test-proxy-unit-a-uv - Run proxy_unit_tests a-o (uv)"
	@echo "  make test-proxy-unit-b-uv - Run proxy_unit_tests p-z (uv)"
	@echo "  make test-integration-uv - Run integration tests (uv)"
	@echo "  make test-llm-translation-uv - Run LLM translation tests (uv)"
	@echo "  make test-llm-translation-single-uv - Run single LLM translation test (uv)"
	@echo ""
	@echo "=== Dependency Sync (Poetry → PEP-621) ==="
	@echo "  make sync-deps          - Sync Poetry deps to PEP-621"
	@echo "  make sync-deps-check    - Check if deps are in sync (CI)"
	@echo "  make sync-deps-dry-run  - Preview sync changes"
	@echo ""
	@echo "=== Other ==="
	@echo "  make install-helm-unittest - Install helm unittest plugin"
	@echo "  make test-unit-helm     - Run helm unit tests"

# Keep PIP simple for edge cases:
PIP := $(shell command -v pip > /dev/null 2>&1 && echo "pip" || echo "python3 -m pip")

# Show info
info:
	@echo "PIP: $(PIP)"

# Installation targets
install-dev:
	poetry install --with dev

install-proxy-dev:
	poetry install --with dev,proxy-dev --extras proxy

# CI-compatible installations (matches GitHub workflows exactly)
install-dev-ci:
	$(PIP) install openai==2.8.0
	poetry install --with dev
	$(PIP) install openai==2.8.0

install-proxy-dev-ci:
	poetry install --with dev,proxy-dev --extras proxy
	$(PIP) install openai==2.8.0

install-test-deps: install-proxy-dev
	poetry run $(PIP) install "pytest-retry==1.6.3"
	poetry run $(PIP) install pytest-xdist
	poetry run $(PIP) install openapi-core
	cd enterprise && poetry run $(PIP) install -e . && cd ..

install-helm-unittest:
	helm plugin install https://github.com/helm-unittest/helm-unittest --version v0.4.4 || echo "ignore error if plugin exists"

# Formatting
format: install-dev
	cd litellm && poetry run black . && cd ..

format-check: install-dev
	cd litellm && poetry run black --check . && cd ..

# Linting targets
lint-ruff: install-dev
	cd litellm && poetry run ruff check . && cd ..

# faster linter for developing ...
# inspiration from:
# https://github.com/astral-sh/ruff/discussions/10977
# https://github.com/astral-sh/ruff/discussions/4049
lint-format-changed: install-dev
	@git diff origin/main --unified=0 --no-color -- '*.py' | \
	perl -ne '\
		if (/^diff --git a\/(.*) b\//) { $$file = $$1; } \
		if (/^@@ .* \+(\d+)(?:,(\d+))? @@/) { \
			$$start = $$1; $$count = $$2 || 1; $$end = $$start + $$count - 1; \
			print "$$file:$$start:1-$$end:999\n"; \
		}' | \
	while read range; do \
		file="$${range%%:*}"; \
		lines="$${range#*:}"; \
		echo "Formatting $$file (lines $$lines)"; \
		poetry run ruff format --range "$$lines" "$$file"; \
	done

lint-ruff-dev: install-dev
	@tmpfile=$$(mktemp /tmp/ruff-dev.XXXXXX) && \
	cd litellm && \
	(poetry run ruff check . --output-format=pylint || true) > "$$tmpfile" && \
	poetry run diff-quality --violations=pylint "$$tmpfile" --compare-branch=origin/main && \
	cd .. ; \
	rm -f "$$tmpfile"

lint-ruff-FULL-dev: install-dev
	@files=$$(git diff --name-only origin/main -- '*.py'); \
	if [ -n "$$files" ]; then echo "$$files" | xargs poetry run ruff check; \
	else echo "No changed .py files to check."; fi

lint-mypy: install-dev
	poetry run $(PIP) install types-requests types-setuptools types-redis types-PyYAML
	cd litellm && poetry run mypy . --ignore-missing-imports && cd ..

lint-black: format-check

check-circular-imports: install-dev
	cd litellm && poetry run python ../tests/documentation_tests/test_circular_imports.py && cd ..

check-import-safety: install-dev
	@poetry run python -c "from litellm import *; print('[from litellm import *] OK! no issues!');" || (echo '🚨 import failed, this means you introduced unprotected imports! 🚨'; exit 1)

# Combined linting (matches test-linting.yml workflow)
lint: format-check lint-ruff lint-mypy check-circular-imports check-import-safety

# Faster linting for local development (only checks changed code)
lint-dev: lint-format-changed lint-mypy check-circular-imports check-import-safety

# Testing targets
test:
	poetry run pytest tests/

test-unit: install-test-deps
	poetry run pytest tests/test_litellm -x -vv -n 4

# Matrix test targets (matching CI workflow groups)
test-unit-llms: install-test-deps
	poetry run pytest tests/test_litellm/llms --tb=short -vv -n 4 --durations=20

test-unit-proxy-guardrails: install-test-deps
	poetry run pytest tests/test_litellm/proxy/guardrails tests/test_litellm/proxy/management_endpoints tests/test_litellm/proxy/management_helpers --tb=short -vv -n 4 --durations=20

test-unit-proxy-core: install-test-deps
	poetry run pytest tests/test_litellm/proxy/auth tests/test_litellm/proxy/client tests/test_litellm/proxy/db tests/test_litellm/proxy/hooks tests/test_litellm/proxy/policy_engine --tb=short -vv -n 4 --durations=20

test-unit-proxy-misc: install-test-deps
	poetry run pytest tests/test_litellm/proxy/_experimental tests/test_litellm/proxy/agent_endpoints tests/test_litellm/proxy/anthropic_endpoints tests/test_litellm/proxy/common_utils tests/test_litellm/proxy/discovery_endpoints tests/test_litellm/proxy/experimental tests/test_litellm/proxy/google_endpoints tests/test_litellm/proxy/health_endpoints tests/test_litellm/proxy/image_endpoints tests/test_litellm/proxy/middleware tests/test_litellm/proxy/openai_files_endpoint tests/test_litellm/proxy/pass_through_endpoints tests/test_litellm/proxy/prompts tests/test_litellm/proxy/public_endpoints tests/test_litellm/proxy/response_api_endpoints tests/test_litellm/proxy/spend_tracking tests/test_litellm/proxy/ui_crud_endpoints tests/test_litellm/proxy/vector_store_endpoints tests/test_litellm/proxy/test_*.py --tb=short -vv -n 4 --durations=20

test-unit-integrations: install-test-deps
	poetry run pytest tests/test_litellm/integrations --tb=short -vv -n 4 --durations=20

test-unit-core-utils: install-test-deps
	poetry run pytest tests/test_litellm/litellm_core_utils --tb=short -vv -n 2 --durations=20

test-unit-other: install-test-deps
	poetry run pytest tests/test_litellm/caching tests/test_litellm/responses tests/test_litellm/secret_managers tests/test_litellm/vector_stores tests/test_litellm/a2a_protocol tests/test_litellm/anthropic_interface tests/test_litellm/completion_extras tests/test_litellm/containers tests/test_litellm/enterprise tests/test_litellm/experimental_mcp_client tests/test_litellm/google_genai tests/test_litellm/images tests/test_litellm/interactions tests/test_litellm/passthrough tests/test_litellm/router_strategy tests/test_litellm/router_utils tests/test_litellm/types --tb=short -vv -n 4 --durations=20

test-unit-root: install-test-deps
	poetry run pytest tests/test_litellm/test_*.py --tb=short -vv -n 4 --durations=20

# Proxy unit tests (tests/proxy_unit_tests split alphabetically)
test-proxy-unit-a: install-test-deps
	poetry run pytest tests/proxy_unit_tests/test_[a-o]*.py --tb=short -vv -n 2 --durations=20

test-proxy-unit-b: install-test-deps
	poetry run pytest tests/proxy_unit_tests/test_[p-z]*.py --tb=short -vv -n 2 --durations=20

test-integration:
	poetry run pytest tests/ -k "not test_litellm"

test-unit-helm: install-helm-unittest
	helm unittest -f 'tests/*.yaml' deploy/charts/litellm-helm

# LLM Translation testing targets
test-llm-translation: install-test-deps
	@echo "Running LLM translation tests..."
	@python .github/workflows/run_llm_translation_tests.py

test-llm-translation-single: install-test-deps
	@echo "Running single LLM translation test file..."
	@if [ -z "$(FILE)" ]; then echo "Usage: make test-llm-translation-single FILE=test_filename.py"; exit 1; fi
	@mkdir -p test-results
	poetry run pytest tests/llm_translation/$(FILE) \
		--junitxml=test-results/junit.xml \
		-v --tb=short --maxfail=100 --timeout=300

# ============================================================
# UV-based targets (PEP-621 compatible)
# ============================================================

# Auto-create venv if it doesn't exist (file target: only runs when .venv is missing)
.venv:
	uv venv --python 3.12

# Installation targets (uv)
install-dev-uv: .venv
	uv pip install -e ".[dev]"

install-proxy-dev-uv: .venv
	uv pip install -e ".[proxy,dev,proxy-dev]"

install-test-deps-uv: install-proxy-dev-uv
	uv pip install "pytest-retry==1.6.3" pytest-xdist openapi-core
	cd enterprise && uv pip install -e . && cd ..

# Formatting (uv)
format-uv: .venv
	$(VENV_ACTIVATE) cd litellm && black . && cd ..

format-check-uv: .venv
	$(VENV_ACTIVATE) cd litellm && black --check . && cd ..

# Linting targets (uv)
lint-ruff-uv: .venv
	$(VENV_ACTIVATE) cd litellm && ruff check . && cd ..

lint-mypy-uv: .venv
	$(VENV_ACTIVATE) cd litellm && mypy . --ignore-missing-imports && cd ..

lint-black-uv: format-check-uv

check-circular-imports-uv: .venv
	$(VENV_ACTIVATE) cd litellm && python ../tests/documentation_tests/test_circular_imports.py && cd ..

check-import-safety-uv: .venv
	$(VENV_ACTIVATE) python -c "from litellm import *" || (echo '🚨 import failed, this means you introduced unprotected imports! 🚨'; exit 1)

# Combined linting (uv)
lint-uv: format-check-uv lint-ruff-uv lint-mypy-uv check-circular-imports-uv check-import-safety-uv

# Testing targets (uv)
test-uv: install-dev-uv
	$(VENV_ACTIVATE) pytest tests/

test-unit-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm -x -vv -n 4

test-integration-uv: install-dev-uv
	$(VENV_ACTIVATE) pytest tests/ -k "not test_litellm"

# Lint dev targets (uv) - faster linting for local development
lint-format-changed-uv: .venv
	@git diff origin/main --unified=0 --no-color -- '*.py' | \
	perl -ne'\
		if (/^diff --git a\/(.*) b\//) { $$file = $$1; } \
		if (/^@@ .* \+(\d+)(?:,(\d+))? @@/) { \
			$$start = $$1; $$count = $$2 || 1; $$end = $$start + $$count - 1; \
			print "$$file:$$start:1-$$end:999\n"; \
		}' | \
	while read range; do \
		file="$${range%%:*}"; \
		lines="$${range#*:}"; \
		echo "Formatting $$file (lines $$lines)"; \
		$(VENV_ACTIVATE) ruff format --range "$$lines" "$$file"; \
	done

lint-ruff-dev-uv: .venv
	@tmpfile=$$(mktemp /tmp/ruff-dev.XXXXXX) && \
	cd litellm && \
	($(VENV_ACTIVATE) ruff check . --output-format=pylint || true) > "$$tmpfile" && \
	$(VENV_ACTIVATE) diff-quality --violations=pylint "$$tmpfile" --compare-branch=origin/main && \
	cd .. ; \
	rm -f "$$tmpfile"

lint-ruff-FULL-dev-uv: .venv
	@files=$$(git diff --name-only origin/main -- '*.py'); \
	if [ -n "$$files" ]; then $(VENV_ACTIVATE) echo "$$files" | xargs ruff check; \
	else echo "No changed .py files to check."; fi

lint-dev-uv: lint-format-changed-uv lint-mypy-uv check-circular-imports-uv check-import-safety-uv

# Matrix test targets (uv) - matching CI workflow groups
test-unit-llms-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/llms --tb=short -vv -n 4 --durations=20

test-unit-proxy-guardrails-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/proxy/guardrails tests/test_litellm/proxy/management_endpoints tests/test_litellm/proxy/management_helpers --tb=short -vv -n 4 --durations=20

test-unit-proxy-core-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/proxy/auth tests/test_litellm/proxy/client tests/test_litellm/proxy/db tests/test_litellm/proxy/hooks tests/test_litellm/proxy/policy_engine --tb=short -vv -n 4 --durations=20

test-unit-proxy-misc-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/proxy/_experimental tests/test_litellm/proxy/agent_endpoints tests/test_litellm/proxy/anthropic_endpoints tests/test_litellm/proxy/common_utils tests/test_litellm/proxy/discovery_endpoints tests/test_litellm/proxy/experimental tests/test_litellm/proxy/google_endpoints tests/test_litellm/proxy/health_endpoints tests/test_litellm/proxy/image_endpoints tests/test_litellm/proxy/middleware tests/test_litellm/proxy/openai_files_endpoint tests/test_litellm/proxy/pass_through_endpoints tests/test_litellm/proxy/prompts tests/test_litellm/proxy/public_endpoints tests/test_litellm/proxy/response_api_endpoints tests/test_litellm/proxy/spend_tracking tests/test_litellm/proxy/ui_crud_endpoints tests/test_litellm/proxy/vector_store_endpoints tests/test_litellm/proxy/test_*.py --tb=short -vv -n 4 --durations=20

test-unit-integrations-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/integrations --tb=short -vv -n 4 --durations=20

test-unit-core-utils-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/litellm_core_utils --tb=short -vv -n 2 --durations=20

test-unit-other-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/caching tests/test_litellm/responses tests/test_litellm/secret_managers tests/test_litellm/vector_stores tests/test_litellm/a2a_protocol tests/test_litellm/anthropic_interface tests/test_litellm/completion_extras tests/test_litellm/containers tests/test_litellm/enterprise tests/test_litellm/experimental_mcp_client tests/test_litellm/google_genai tests/test_litellm/images tests/test_litellm/interactions tests/test_litellm/passthrough tests/test_litellm/router_strategy tests/test_litellm/router_utils tests/test_litellm/types --tb=short -vv -n 4 --durations=20

test-unit-root-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/test_litellm/test_*.py --tb=short -vv -n 4 --durations=20

# Proxy unit tests (uv) - split alphabetically
test-proxy-unit-a-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/proxy_unit_tests/test_[a-o]*.py --tb=short -vv -n 2 --durations=20

test-proxy-unit-b-uv: install-test-deps-uv
	$(VENV_ACTIVATE) pytest tests/proxy_unit_tests/test_[p-z]*.py --tb=short -vv -n 2 --durations=20

# LLM Translation tests (uv)
test-llm-translation-uv: install-test-deps-uv
	@echo "Running LLM translation tests..."
	@$(VENV_ACTIVATE) python .github/workflows/run_llm_translation_tests.py

test-llm-translation-single-uv: install-test-deps-uv
	@echo "Running single LLM translation test file..."
	@if [ -z "$(FILE)" ]; then echo "Usage: make test-llm-translation-single-uv FILE=test_filename.py"; exit 1; fi
	@mkdir -p test-results
	$(VENV_ACTIVATE) pytest tests/llm_translation/$(FILE) \
		--junitxml=test-results/junit.xml \
		-v --tb=short --maxfail=100 --timeout=300

# ============================================================
# Dependency sync targets (Poetry -> PEP-621)
# ============================================================

sync-deps:
	@echo "Syncing Poetry dependencies to PEP-621 format..."
	uv run --with tomlkit python scripts/sync_poetry_to_pep621.py

sync-deps-check:
	@echo "Checking if dependencies are in sync..."
	uv run --with tomlkit python scripts/sync_poetry_to_pep621.py --check

sync-deps-dry-run:
	@echo "Preview sync changes (dry-run)..."
	uv run --with tomlkit python scripts/sync_poetry_to_pep621.py --dry-run
