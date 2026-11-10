# Incident Copilot — task runner.
# On Windows, run these from Git Bash (comes with Git for Windows), e.g.:  make check
# Cluster targets are implemented in Milestone M1.

.PHONY: install verify-llm fmt lint types test check \
        cluster-up cluster-stop cluster-start cluster-down

install:          ## Install deps into .venv from the lockfile
	uv sync --locked

verify-llm:       ## Check all LLM providers + tool calling work
	uv run python scripts/verify_llm.py

fmt:              ## Auto-format and auto-fix
	uv run ruff format .
	uv run ruff check --fix .

lint:             ## Lint + format check (no changes)
	uv run ruff check .
	uv run ruff format --check .

types:            ## Static type check
	uv run mypy

test:             ## Run tests
	uv run pytest -q

check: lint types test  ## Everything CI runs

# --- Cluster lifecycle (M1) ---
cluster-up:
	@echo "M1: creates k3d cluster + mini-shop + observability"
cluster-stop:
	@echo "M1: k3d cluster stop (frees RAM, replay mode)"
cluster-start:
	@echo "M1: k3d cluster start"
cluster-down:
	@echo "M1: k3d cluster delete"
