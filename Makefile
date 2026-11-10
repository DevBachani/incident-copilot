# Incident Copilot — task runner.
# On Windows, run these from Git Bash (comes with Git for Windows), e.g.:  make check
# Cluster targets are implemented in Milestone M1.

.PHONY: install verify-llm fmt lint types test check \
        cluster-up cluster-stop cluster-start cluster-down inject clear

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

# --- Cluster lifecycle (M1) ---  (needs k3d + helm on PATH; Docker Desktop running)
CLUSTER := incident

cluster-up:       ## Create cluster + deploy mini-shop & observability
	k3d cluster create --config infra/k3d-config.yaml || k3d cluster start $(CLUSTER)
	docker build -f shop/Dockerfile -t mini-shop:dev .
	k3d image import mini-shop:dev -c $(CLUSTER)
	kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f infra/observability/
	helm upgrade --install mini-shop shop/helm/mini-shop -n shop --create-namespace
	@echo "Shop: http://localhost:8080  Prometheus: http://localhost:9090  Jaeger: http://localhost:16686"

cluster-stop:     ## Stop cluster (frees RAM; replay mode)
	k3d cluster stop $(CLUSTER)

cluster-start:    ## Start the stopped cluster
	k3d cluster start $(CLUSTER)

cluster-down:     ## Delete the cluster
	k3d cluster delete $(CLUSTER)

inject:           ## Inject a fault scenario:  make inject S=payment-errors-01
	uv run python faults/inject.py inject $(S)

clear:            ## Clear a fault scenario:   make clear S=payment-errors-01
	uv run python faults/inject.py clear $(S)
