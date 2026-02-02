<<<<<<< HEAD
.PHONY: help install install-dev setup lint format type-check test test-cov test-unit test-integration clean pre-commit gpu-check ollama-check docs build publish demo-setup demo-cluster-create demo-cluster-delete demo-app-deploy demo-incident-inject demo-clean

# Default shell
SHELL := /bin/bash

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Project settings
PROJECT_NAME := aegis
PYTHON := python3.12
UV := uv

# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    OPEN := xdg-open
else ifeq ($(UNAME_S),Darwin)
    OPEN := open
else
    OPEN := start
endif

##@ General

help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

install: ## Install production dependencies only
	@echo -e "$(BLUE)Installing production dependencies...$(NC)"
	$(UV) sync --frozen --no-dev
	@echo -e "$(GREEN)✓ Production dependencies installed$(NC)"

install-dev: ## Install all dependencies including dev
	@echo -e "$(BLUE)Installing all dependencies (including dev)...$(NC)"
	$(UV) sync --frozen --all-extras
	@echo -e "$(GREEN)✓ All dependencies installed$(NC)"

setup: ## Complete project setup for new developers
	@echo -e "$(BLUE)Setting up AEGIS development environment...$(NC)"
	@echo ""
	@echo -e "$(YELLOW)Step 1/6: Checking Python version...$(NC)"
	@$(PYTHON) --version || (echo -e "$(RED)Python 3.12 not found. Please install it first.$(NC)" && exit 1)
	@echo ""
	@echo -e "$(YELLOW)Step 2/6: Checking uv installation...$(NC)"
	@command -v $(UV) >/dev/null 2>&1 || (echo -e "$(YELLOW)Installing uv...$(NC)" && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo ""
	@echo -e "$(YELLOW)Step 3/6: Installing dependencies...$(NC)"
	$(UV) sync --frozen --all-extras
	@echo ""
	@echo -e "$(YELLOW)Step 4/6: Setting up pre-commit hooks...$(NC)"
	$(UV) run pre-commit install
	$(UV) run pre-commit install --hook-type commit-msg
	@echo ""
	@echo -e "$(YELLOW)Step 5/6: Creating local environment file...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env && echo -e "$(GREEN)Created .env from .env.example$(NC)"; else echo -e "$(GREEN).env already exists$(NC)"; fi
	@echo ""
	@echo -e "$(YELLOW)Step 6/6: Checking GPU configuration...$(NC)"
	@$(MAKE) gpu-check || true
	@echo ""
	@echo -e "$(GREEN)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║                    AEGIS Setup Complete!                     ║$(NC)"
	@echo -e "$(GREEN)╠══════════════════════════════════════════════════════════════╣$(NC)"
	@echo -e "$(GREEN)║  Next steps:                                                  ║$(NC)"
	@echo -e "$(GREEN)║  1. Edit .env with your settings                             ║$(NC)"
	@echo -e "$(GREEN)║  2. Run 'make test' to verify everything works               ║$(NC)"
	@echo -e "$(GREEN)║  3. Run 'make lint' to check code quality                    ║$(NC)"
	@echo -e "$(GREEN)╚══════════════════════════════════════════════════════════════╝$(NC)"

##@ Quality

lint: ## Run all linters (ruff)
	@echo -e "$(BLUE)Running ruff linter...$(NC)"
	$(UV) run ruff check src/ tests/
	@echo -e "$(GREEN)✓ Linting passed$(NC)"

format: ## Format code with ruff
	@echo -e "$(BLUE)Formatting code...$(NC)"
	$(UV) run ruff format src/ tests/
	$(UV) run ruff check --fix src/ tests/
	@echo -e "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run mypy type checking
	@echo -e "$(BLUE)Running type checks...$(NC)"
	$(UV) run mypy src/
	@echo -e "$(GREEN)✓ Type checking passed$(NC)"

security: ## Run security checks (bandit + safety)
	@echo -e "$(BLUE)Running security checks...$(NC)"
	$(UV) run bandit -r src/ -c pyproject.toml
	$(UV) run pip-audit
	@echo -e "$(GREEN)✓ Security checks passed$(NC)"

pre-commit: ## Run all pre-commit hooks
	@echo -e "$(BLUE)Running pre-commit hooks...$(NC)"
	$(UV) run pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	@echo -e "$(BLUE)Updating pre-commit hooks...$(NC)"
	$(UV) run pre-commit autoupdate

check-all: lint type-check security ## Run all checks (lint, type-check, security)
	@echo -e "$(GREEN)✓ All checks passed$(NC)"

##@ Testing

test: ## Run tests (excluding slow/integration)
	@echo -e "$(BLUE)Running tests...$(NC)"
	$(UV) run pytest tests/ -v --ignore=tests/integration

test-unit: ## Run unit tests only
	@echo -e "$(BLUE)Running unit tests...$(NC)"
	$(UV) run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo -e "$(BLUE)Running integration tests...$(NC)"
	$(UV) run pytest tests/integration/ -v

test-cov: ## Run tests with coverage report
	@echo -e "$(BLUE)Running tests with coverage...$(NC)"
	$(UV) run pytest tests/ \
		--cov=aegis \
		--cov-report=term-missing:skip-covered \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-branch \
		--cov-fail-under=80 \
		--ignore=tests/integration
	@echo -e "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"
	@$(OPEN) htmlcov/index.html 2>/dev/null || true

test-benchmark: ## Run benchmark tests
	@echo -e "$(BLUE)Running benchmarks...$(NC)"
	$(UV) run pytest tests/benchmarks/ -v --benchmark-only

test-watch: ## Run tests in watch mode
	@echo -e "$(BLUE)Running tests in watch mode...$(NC)"
	$(UV) run pytest-watch -- tests/unit/ -v

test-all: ## Run complete test suite (unit + integration + docker + observability)
	@echo -e "$(BLUE)Running complete test suite...$(NC)"
	@chmod +x scripts/test-all.sh
	@./scripts/test-all.sh

##@ GPU & Ollama

gpu-check: ## Check GPU availability and configuration
	@echo -e "$(BLUE)Checking GPU configuration...$(NC)"
	@echo ""
	@if command -v nvidia-smi >/dev/null 2>&1; then \
		echo -e "$(GREEN)NVIDIA GPU detected:$(NC)"; \
		nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader; \
		echo ""; \
		echo -e "$(YELLOW)Recommended models based on VRAM:$(NC)"; \
		VRAM=$$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' '); \
		if [ "$$VRAM" -ge 16000 ]; then \
			echo "  - llama3.2:8b, mistral:7b, codellama:13b"; \
		elif [ "$$VRAM" -ge 8000 ]; then \
			echo "  - llama3.2:3b, phi3:mini, qwen2:7b"; \
		elif [ "$$VRAM" -ge 6000 ]; then \
			echo "  - tinyllama:1b, phi3:mini, qwen2:1.5b"; \
		else \
			echo "  - tinyllama:1b, phi3:mini (may be slow)"; \
		fi; \
	else \
		echo -e "$(YELLOW)No NVIDIA GPU detected.$(NC)"; \
		echo "Options:"; \
		echo "  1. Use CPU-only mode (slow)"; \
		echo "  2. Use cloud APIs (Groq, Gemini, Together AI)"; \
		echo "  3. Configure OLLAMA_HOST to use remote Ollama server"; \
	fi
	@echo ""

ollama-check: ## Check Ollama installation and running models
	@echo -e "$(BLUE)Checking Ollama status...$(NC)"
	@if command -v ollama >/dev/null 2>&1; then \
		echo -e "$(GREEN)Ollama installed:$(NC) $$(ollama --version)"; \
		echo ""; \
		echo -e "$(YELLOW)Available models:$(NC)"; \
		ollama list 2>/dev/null || echo "  (Ollama service not running)"; \
	else \
		echo -e "$(YELLOW)Ollama not installed.$(NC)"; \
		echo "Install: curl -fsSL https://ollama.com/install.sh | sh"; \
	fi

ollama-pull: ## Pull recommended models for your GPU
	@echo -e "$(BLUE)Pulling recommended Ollama models...$(NC)"
	@if command -v nvidia-smi >/dev/null 2>&1; then \
		VRAM=$$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' '); \
		if [ "$$VRAM" -ge 8000 ]; then \
			echo "Pulling llama3.2:3b for 8GB+ VRAM..."; \
			ollama pull llama3.2:3b; \
		else \
			echo "Pulling tinyllama:1b for <8GB VRAM..."; \
			ollama pull tinyllama:1b; \
		fi; \
	else \
		echo "No GPU detected, pulling tinyllama:1b (CPU-friendly)..."; \
		ollama pull tinyllama:1b; \
	fi

##@ Kubernetes

k8s-check: ## Check Kubernetes cluster connection
	@echo -e "$(BLUE)Checking Kubernetes connection...$(NC)"
	@kubectl cluster-info 2>/dev/null || (echo -e "$(RED)Cannot connect to Kubernetes cluster$(NC)" && exit 1)
	@echo -e "$(GREEN)✓ Connected to Kubernetes$(NC)"

k8s-crds: ## Install AEGIS CRDs to cluster
	@echo -e "$(BLUE)Installing CRDs...$(NC)"
	kubectl apply -f deploy/kustomize/base/crds/
	@echo -e "$(GREEN)✓ CRDs installed$(NC)"

helm-lint: ## Lint Helm charts
	@echo -e "$(BLUE)Linting Helm charts...$(NC)"
	helm lint deploy/helm/aegis-operator/
	@echo -e "$(GREEN)✓ Helm charts valid$(NC)"

helm-template: ## Render Helm templates locally
	@echo -e "$(BLUE)Rendering Helm templates...$(NC)"
	helm template aegis deploy/helm/aegis-operator/ --debug

##@ Documentation

docs: ## Build documentation
	@echo -e "$(BLUE)Building documentation...$(NC)"
	$(UV) run mkdocs build
	@echo -e "$(GREEN)✓ Documentation built in site/$(NC)"

docs-serve: ## Serve documentation locally
	@echo -e "$(BLUE)Serving documentation at http://localhost:8000...$(NC)"
	$(UV) run mkdocs serve

##@ Build & Release

build: clean ## Build distribution packages
	@echo -e "$(BLUE)Building packages...$(NC)"
	$(UV) build
	@echo -e "$(GREEN)✓ Packages built in dist/$(NC)"

docker-build: ## Build Docker image
	@echo -e "$(BLUE)Building Docker image...$(NC)"
	docker build -t aegis-operator:latest -f deploy/docker/Dockerfile .
	@echo -e "$(GREEN)✓ Docker image built$(NC)"

docker-push: ## Push Docker image to registry
	@echo -e "$(BLUE)Pushing Docker image...$(NC)"
	docker push aegis-operator:latest
	@echo -e "$(GREEN)✓ Docker image pushed$(NC)"

publish: build ## Publish to PyPI (requires credentials)
	@echo -e "$(BLUE)Publishing to PyPI...$(NC)"
	$(UV) publish
	@echo -e "$(GREEN)✓ Published to PyPI$(NC)"

##@ Development

run: ## Run the operator locally
	@echo -e "$(BLUE)Starting AEGIS operator...$(NC)"
	$(UV) run python -m aegis.k8s_operator.main

run-dev: ## Run the operator in development mode with auto-reload
	@echo -e "$(BLUE)Starting AEGIS operator in dev mode...$(NC)"
	$(UV) run kopf run src/aegis/k8s_operator/main.py --dev --verbose

shell: ## Open Python shell with project context
	@echo -e "$(BLUE)Opening Python shell...$(NC)"
	$(UV) run python -i -c "from aegis import *; print('AEGIS modules loaded')"

repl: ## Open IPython shell
	@echo -e "$(BLUE)Opening IPython shell...$(NC)"
	$(UV) run ipython

##@ Cleanup

clean: ## Clean build artifacts
	@echo -e "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf site/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo -e "$(GREEN)✓ Cleaned$(NC)"

clean-all: clean ## Clean everything including .venv
	@echo -e "$(BLUE)Cleaning everything including virtual environment...$(NC)"
	rm -rf .venv/
	@echo -e "$(GREEN)✓ Full clean complete$(NC)"

##@ Info

version: ## Show project version
	@$(UV) run python -c "from aegis import __version__; print(__version__)"

info: ## Show project info
	@echo -e "$(BLUE)AEGIS Project Info$(NC)"
	@echo "===================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "UV: $$($(UV) --version)"
	@echo "Project: $(PROJECT_NAME)"
	@echo ""
	@echo "Installed packages:"
	@$(UV) pip list --format=freeze | head -20

##@ Demo Environment

demo-setup: ## Install all demo prerequisites (Kind, K8sGPT, vCluster, Ollama)
	@echo -e "$(BLUE)Setting up demo environment...$(NC)"
	@chmod +x scripts/demo-setup.sh
	@./scripts/demo-setup.sh

demo-cluster-create: ## Create Kind cluster for demos
	@echo -e "$(BLUE)Creating Kind cluster 'aegis-demo'...$(NC)"
	@kind create cluster --config examples/cluster/kind-config.yaml --name aegis-demo
	@kubectl wait --for=condition=Ready nodes --all --timeout=120s
	@echo -e "$(GREEN)✓ Cluster created$(NC)"

demo-cluster-delete: ## Delete Kind demo cluster
	@echo -e "$(YELLOW)Deleting Kind cluster 'aegis-demo'...$(NC)"
	@kind delete cluster --name aegis-demo
	@echo -e "$(GREEN)✓ Cluster deleted$(NC)"

demo-app-deploy: ## Deploy demo application to cluster
	@echo -e "$(BLUE)Deploying demo application...$(NC)"
	@kubectl apply -k examples/demo-app/
	@echo -e "$(BLUE)Waiting for pods to be ready...$(NC)"
	@kubectl wait --for=condition=Ready pod -l app=demo-db -n production --timeout=120s || true
	@kubectl wait --for=condition=Ready pod -l app=demo-redis -n production --timeout=60s || true
	@kubectl wait --for=condition=Ready pod -l app=demo-api -n production --timeout=120s || true
	@echo -e "$(GREEN)✓ Demo app deployed$(NC)"
	@kubectl get pods -n production

demo-app-status: ## Show status of demo application
	@echo -e "$(BLUE)Demo Application Status$(NC)"
	@echo "========================"
	@kubectl get pods -n production -o wide
	@echo ""
	@echo -e "$(BLUE)Services:$(NC)"
	@kubectl get svc -n production
	@echo ""
	@echo -e "$(BLUE)Recent Events:$(NC)"
	@kubectl get events -n production --sort-by='.lastTimestamp' | tail -10

demo-incident-crashloop: ## Inject CrashLoopBackOff incident
	@echo -e "$(YELLOW)Injecting CrashLoopBackOff incident...$(NC)"
	@kubectl apply -f examples/incidents/crashloop-missing-env.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-oomkill: ## Inject OOMKilled incident
	@echo -e "$(YELLOW)Injecting OOMKilled incident...$(NC)"
	@kubectl apply -f examples/incidents/oomkill-memory-leak.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-imagepull: ## Inject ImagePullBackOff incident
	@echo -e "$(YELLOW)Injecting ImagePullBackOff incident...$(NC)"
	@kubectl apply -f examples/incidents/imagepull-bad-tag.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-pending: ## Inject Pending pod incident
	@echo -e "$(YELLOW)Injecting Pending pod incident...$(NC)"
	@kubectl apply -f examples/incidents/pending-no-resources.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl describe pod -l app=demo-api -n production$(NC)"

demo-incident-liveness: ## Inject Liveness probe failure incident
	@echo -e "$(YELLOW)Injecting Liveness probe failure...$(NC)"
	@kubectl apply -f examples/incidents/liveness-failure.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-reset: ## Reset demo app to healthy state
	@echo -e "$(BLUE)Resetting demo app to healthy state...$(NC)"
	@kubectl apply -f examples/demo-app/demo-api.yaml
	@kubectl rollout restart deployment/demo-api -n production
	@kubectl wait --for=condition=Ready pod -l app=demo-api -n production --timeout=120s
	@echo -e "$(GREEN)✓ Demo app reset to healthy state$(NC)"

demo-k8sgpt-analyze: ## Run K8sGPT analysis on cluster
	@echo -e "$(BLUE)Running K8sGPT analysis...$(NC)"
	@k8sgpt analyze --filter=Pod --namespace=production --explain

demo-k8sgpt-config: ## Configure K8sGPT with Ollama backend
	@echo -e "$(BLUE)Configuring K8sGPT with Ollama...$(NC)"
	@k8sgpt auth remove --backend ollama 2>/dev/null || true
	@k8sgpt auth add --backend ollama --baseurl http://localhost:11434 --model phi3:mini
	@echo -e "$(GREEN)✓ K8sGPT configured$(NC)"

demo-aegis-analyze: ## Run AEGIS analysis on demo-api pod
	@echo -e "$(BLUE)Running AEGIS analysis...$(NC)"
	$(UV) run aegis analyze pod/demo-api --namespace production

demo-shadow-create: ## Create a shadow environment for testing
	@echo -e "$(BLUE)Creating shadow environment...$(NC)"
	@vcluster create shadow-test -n aegis-shadows -f examples/shadow/vcluster-template.yaml --connect=false
	@echo -e "$(GREEN)✓ Shadow environment created$(NC)"

demo-shadow-list: ## List shadow environments
	@echo -e "$(BLUE)Shadow Environments:$(NC)"
	@vcluster list

demo-shadow-delete: ## Delete test shadow environment
	@echo -e "$(YELLOW)Deleting shadow environment...$(NC)"
	@vcluster delete shadow-test -n aegis-shadows
	@echo -e "$(GREEN)✓ Shadow environment deleted$(NC)"

demo-clean: ## Clean up all demo resources
	@echo -e "$(YELLOW)Cleaning up demo resources...$(NC)"
	@kubectl delete namespace production --ignore-not-found=true || true
	@kubectl delete namespace aegis-shadows --ignore-not-found=true || true
	@kubectl delete namespace aegis-system --ignore-not-found=true || true
	@echo -e "$(GREEN)✓ Demo resources cleaned$(NC)"

demo-full: demo-cluster-create demo-app-deploy ## Full demo setup (cluster + app)
	@echo ""
	@echo -e "$(GREEN)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║                    Demo Environment Ready!                   ║$(NC)"
	@echo -e "$(GREEN)╠══════════════════════════════════════════════════════════════╣$(NC)"
	@echo -e "$(GREEN)║  Demo API: http://localhost:30000                            ║$(NC)"
	@echo -e "$(GREEN)║                                                              ║$(NC)"
	@echo -e "$(GREEN)║  Inject an incident:                                         ║$(NC)"
	@echo -e "$(GREEN)║    make demo-incident-crashloop                              ║$(NC)"
	@echo -e "$(GREEN)║    make demo-incident-oomkill                                ║$(NC)"
	@echo -e "$(GREEN)║                                                              ║$(NC)"
	@echo -e "$(GREEN)║  Analyze with AEGIS:                                         ║$(NC)"
	@echo -e "$(GREEN)║    make demo-aegis-analyze                                   ║$(NC)"
	@echo -e "$(GREEN)╚══════════════════════════════════════════════════════════════╝$(NC)"
=======
.PHONY: help install install-dev setup lint format type-check test test-cov test-unit test-integration clean pre-commit gpu-check ollama-check docs build publish demo-setup demo-cluster-create demo-cluster-delete demo-app-deploy demo-incident-inject demo-clean

# Default shell
SHELL := /bin/bash

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Project settings
PROJECT_NAME := aegis
PYTHON := python3.12
UV := uv
KIND_NODE_IMAGE ?= kindest/node:v1.30.0
KIND_ROOTLESS_ENV :=
ifneq (,$(findstring /run/user/,$(DOCKER_HOST)))
KIND_ROOTLESS_ENV := KIND_EXPERIMENTAL_ROOTLESS=1
endif

# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    OPEN := xdg-open
else ifeq ($(UNAME_S),Darwin)
    OPEN := open
else
    OPEN := start
endif

##@ General

help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

install: ## Install production dependencies only
	@echo -e "$(BLUE)Installing production dependencies...$(NC)"
	$(UV) sync --frozen --no-dev
	@echo -e "$(GREEN)✓ Production dependencies installed$(NC)"

install-dev: ## Install all dependencies including dev
	@echo -e "$(BLUE)Installing all dependencies (including dev)...$(NC)"
	$(UV) sync --frozen --all-extras
	@echo -e "$(GREEN)✓ All dependencies installed$(NC)"

setup: ## Complete project setup for new developers
	@echo -e "$(BLUE)Setting up AEGIS development environment...$(NC)"
	@echo ""
	@echo -e "$(YELLOW)Step 1/6: Checking Python version...$(NC)"
	@$(PYTHON) --version || (echo -e "$(RED)Python 3.12 not found. Please install it first.$(NC)" && exit 1)
	@echo ""
	@echo -e "$(YELLOW)Step 2/6: Checking uv installation...$(NC)"
	@command -v $(UV) >/dev/null 2>&1 || (echo -e "$(YELLOW)Installing uv...$(NC)" && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo ""
	@echo -e "$(YELLOW)Step 3/6: Installing dependencies...$(NC)"
	$(UV) sync --frozen --all-extras
	@echo ""
	@echo -e "$(YELLOW)Step 4/6: Setting up pre-commit hooks...$(NC)"
	$(UV) run pre-commit install
	$(UV) run pre-commit install --hook-type commit-msg
	@echo ""
	@echo -e "$(YELLOW)Step 5/6: Creating local environment file...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env && echo -e "$(GREEN)Created .env from .env.example$(NC)"; else echo -e "$(GREEN).env already exists$(NC)"; fi
	@echo ""
	@echo -e "$(YELLOW)Step 6/6: Checking GPU configuration...$(NC)"
	@$(MAKE) gpu-check || true
	@echo ""
	@echo -e "$(GREEN)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║                    AEGIS Setup Complete!                     ║$(NC)"
	@echo -e "$(GREEN)╠══════════════════════════════════════════════════════════════╣$(NC)"
	@echo -e "$(GREEN)║  Next steps:                                                  ║$(NC)"
	@echo -e "$(GREEN)║  1. Edit .env with your settings                             ║$(NC)"
	@echo -e "$(GREEN)║  2. Run 'make test' to verify everything works               ║$(NC)"
	@echo -e "$(GREEN)║  3. Run 'make lint' to check code quality                    ║$(NC)"
	@echo -e "$(GREEN)╚══════════════════════════════════════════════════════════════╝$(NC)"

##@ Quality

lint: ## Run all linters (ruff)
	@echo -e "$(BLUE)Running ruff linter...$(NC)"
	$(UV) run ruff check src/ tests/
	@echo -e "$(GREEN)✓ Linting passed$(NC)"

format: ## Format code with ruff
	@echo -e "$(BLUE)Formatting code...$(NC)"
	$(UV) run ruff format src/ tests/
	$(UV) run ruff check --fix src/ tests/
	@echo -e "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run mypy type checking
	@echo -e "$(BLUE)Running type checks...$(NC)"
	$(UV) run mypy src/
	@echo -e "$(GREEN)✓ Type checking passed$(NC)"

security: ## Run security checks (bandit + safety)
	@echo -e "$(BLUE)Running security checks...$(NC)"
	$(UV) run bandit -r src/ -c pyproject.toml
	$(UV) run pip-audit
	@echo -e "$(GREEN)✓ Security checks passed$(NC)"

pre-commit: ## Run all pre-commit hooks
	@echo -e "$(BLUE)Running pre-commit hooks...$(NC)"
	$(UV) run pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	@echo -e "$(BLUE)Updating pre-commit hooks...$(NC)"
	$(UV) run pre-commit autoupdate

check-all: lint type-check security ## Run all checks (lint, type-check, security)
	@echo -e "$(GREEN)✓ All checks passed$(NC)"

##@ Testing

test: ## Run tests (excluding slow/integration)
	@echo -e "$(BLUE)Running tests...$(NC)"
	$(UV) run pytest tests/ -v --ignore=tests/integration

test-unit: ## Run unit tests only
	@echo -e "$(BLUE)Running unit tests...$(NC)"
	$(UV) run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo -e "$(BLUE)Running integration tests...$(NC)"
	$(UV) run pytest tests/integration/ -v

test-cov: ## Run tests with coverage report
	@echo -e "$(BLUE)Running tests with coverage...$(NC)"
	$(UV) run pytest tests/ \
		--cov=aegis \
		--cov-report=term-missing:skip-covered \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-branch \
		--cov-fail-under=80 \
		--ignore=tests/integration
	@echo -e "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"
	@$(OPEN) htmlcov/index.html 2>/dev/null || true

test-benchmark: ## Run benchmark tests
	@echo -e "$(BLUE)Running benchmarks...$(NC)"
	$(UV) run pytest tests/benchmarks/ -v --benchmark-only

test-watch: ## Run tests in watch mode
	@echo -e "$(BLUE)Running tests in watch mode...$(NC)"
	$(UV) run pytest-watch -- tests/unit/ -v

test-all: ## Run complete test suite (unit + integration + docker + observability)
	@echo -e "$(BLUE)Running complete test suite...$(NC)"
	@chmod +x scripts/test-all.sh
	@./scripts/test-all.sh

##@ GPU & Ollama

gpu-check: ## Check GPU availability and configuration
	@echo -e "$(BLUE)Checking GPU configuration...$(NC)"
	@echo ""
	@if command -v nvidia-smi >/dev/null 2>&1; then \
		echo -e "$(GREEN)NVIDIA GPU detected:$(NC)"; \
		nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader; \
		echo ""; \
		echo -e "$(YELLOW)Recommended models based on VRAM:$(NC)"; \
		VRAM=$$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' '); \
		if [ "$$VRAM" -ge 16000 ]; then \
			echo "  - llama3.2:8b, mistral:7b, codellama:13b"; \
		elif [ "$$VRAM" -ge 8000 ]; then \
			echo "  - llama3.2:3b, phi3:mini, qwen2:7b"; \
		elif [ "$$VRAM" -ge 6000 ]; then \
			echo "  - tinyllama:1b, phi3:mini, qwen2:1.5b"; \
		else \
			echo "  - tinyllama:1b, phi3:mini (may be slow)"; \
		fi; \
	else \
		echo -e "$(YELLOW)No NVIDIA GPU detected.$(NC)"; \
		echo "Options:"; \
		echo "  1. Use CPU-only mode (slow)"; \
		echo "  2. Use cloud APIs (Groq, Gemini, Together AI)"; \
		echo "  3. Configure OLLAMA_HOST to use remote Ollama server"; \
	fi
	@echo ""

ollama-check: ## Check Ollama installation and running models
	@echo -e "$(BLUE)Checking Ollama status...$(NC)"
	@if command -v ollama >/dev/null 2>&1; then \
		echo -e "$(GREEN)Ollama installed:$(NC) $$(ollama --version)"; \
		echo ""; \
		echo -e "$(YELLOW)Available models:$(NC)"; \
		ollama list 2>/dev/null || echo "  (Ollama service not running)"; \
	else \
		echo -e "$(YELLOW)Ollama not installed.$(NC)"; \
		echo "Install: curl -fsSL https://ollama.com/install.sh | sh"; \
	fi

ollama-pull: ## Pull recommended models for your GPU
	@echo -e "$(BLUE)Pulling recommended Ollama models...$(NC)"
	@if command -v nvidia-smi >/dev/null 2>&1; then \
		VRAM=$$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' '); \
		if [ "$$VRAM" -ge 8000 ]; then \
			echo "Pulling llama3.2:3b for 8GB+ VRAM..."; \
			ollama pull llama3.2:3b; \
		else \
			echo "Pulling tinyllama:1b for <8GB VRAM..."; \
			ollama pull tinyllama:1b; \
		fi; \
	else \
		echo "No GPU detected, pulling tinyllama:1b (CPU-friendly)..."; \
		ollama pull tinyllama:1b; \
	fi

##@ Kubernetes

k8s-check: ## Check Kubernetes cluster connection
	@echo -e "$(BLUE)Checking Kubernetes connection...$(NC)"
	@kubectl cluster-info 2>/dev/null || (echo -e "$(RED)Cannot connect to Kubernetes cluster$(NC)" && exit 1)
	@echo -e "$(GREEN)✓ Connected to Kubernetes$(NC)"

k8s-crds: ## Install AEGIS CRDs to cluster
	@echo -e "$(BLUE)Installing CRDs...$(NC)"
	kubectl apply -f deploy/kustomize/base/crds/
	@echo -e "$(GREEN)✓ CRDs installed$(NC)"

helm-lint: ## Lint Helm charts
	@echo -e "$(BLUE)Linting Helm charts...$(NC)"
	helm lint deploy/helm/aegis-operator/
	@echo -e "$(GREEN)✓ Helm charts valid$(NC)"

helm-template: ## Render Helm templates locally
	@echo -e "$(BLUE)Rendering Helm templates...$(NC)"
	helm template aegis deploy/helm/aegis-operator/ --debug

##@ Documentation

docs: ## Build documentation
	@echo -e "$(BLUE)Building documentation...$(NC)"
	$(UV) run mkdocs build
	@echo -e "$(GREEN)✓ Documentation built in site/$(NC)"

docs-serve: ## Serve documentation locally
	@echo -e "$(BLUE)Serving documentation at http://localhost:8000...$(NC)"
	$(UV) run mkdocs serve

##@ Build & Release

build: clean ## Build distribution packages
	@echo -e "$(BLUE)Building packages...$(NC)"
	$(UV) build
	@echo -e "$(GREEN)✓ Packages built in dist/$(NC)"

docker-build: ## Build Docker image
	@echo -e "$(BLUE)Building Docker image...$(NC)"
	docker build -t aegis-operator:latest -f deploy/docker/Dockerfile .
	@echo -e "$(GREEN)✓ Docker image built$(NC)"

docker-push: ## Push Docker image to registry
	@echo -e "$(BLUE)Pushing Docker image...$(NC)"
	docker push aegis-operator:latest
	@echo -e "$(GREEN)✓ Docker image pushed$(NC)"

publish: build ## Publish to PyPI (requires credentials)
	@echo -e "$(BLUE)Publishing to PyPI...$(NC)"
	$(UV) publish
	@echo -e "$(GREEN)✓ Published to PyPI$(NC)"

##@ Development

run: ## Run the operator locally
	@echo -e "$(BLUE)Starting AEGIS operator...$(NC)"
	$(UV) run python -m aegis.k8s_operator.main

run-dev: ## Run the operator in development mode with auto-reload
	@echo -e "$(BLUE)Starting AEGIS operator in dev mode...$(NC)"
	$(UV) run kopf run src/aegis/k8s_operator/main.py --dev --verbose

shell: ## Open Python shell with project context
	@echo -e "$(BLUE)Opening Python shell...$(NC)"
	$(UV) run python -i -c "from aegis import *; print('AEGIS modules loaded')"

repl: ## Open IPython shell
	@echo -e "$(BLUE)Opening IPython shell...$(NC)"
	$(UV) run ipython

##@ Cleanup

clean: ## Clean build artifacts
	@echo -e "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf site/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo -e "$(GREEN)✓ Cleaned$(NC)"

clean-all: clean ## Clean everything including .venv
	@echo -e "$(BLUE)Cleaning everything including virtual environment...$(NC)"
	rm -rf .venv/
	@echo -e "$(GREEN)✓ Full clean complete$(NC)"

##@ Info

version: ## Show project version
	@$(UV) run python -c "from aegis import __version__; print(__version__)"

info: ## Show project info
	@echo -e "$(BLUE)AEGIS Project Info$(NC)"
	@echo "===================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "UV: $$($(UV) --version)"
	@echo "Project: $(PROJECT_NAME)"
	@echo ""
	@echo "Installed packages:"
	@$(UV) pip list --format=freeze | head -20

##@ Demo Environment

demo-setup: ## Install all demo prerequisites (Kind, K8sGPT, vCluster, Ollama)
	@echo -e "$(BLUE)Setting up demo environment...$(NC)"
	@chmod +x scripts/demo-setup.sh
	@./scripts/demo-setup.sh

demo-cluster-create: ## Create Kind cluster for demos
	@echo -e "$(BLUE)Creating Kind cluster 'aegis-demo'...$(NC)"
	@env -u KIND_EXPERIMENTAL_CONTAINERD_SNAPSHOTTER $(KIND_ROOTLESS_ENV) kind create cluster \
		--config examples/cluster/kind-config.yaml \
		--name aegis-demo \
		--image $(KIND_NODE_IMAGE)
	@kubectl wait --for=condition=Ready nodes --all --timeout=120s
	@echo -e "$(GREEN)✓ Cluster created$(NC)"

demo-cluster-delete: ## Delete Kind demo cluster
	@echo -e "$(YELLOW)Deleting Kind cluster 'aegis-demo'...$(NC)"
	@kind delete cluster --name aegis-demo
	@echo -e "$(GREEN)✓ Cluster deleted$(NC)"

demo-app-deploy: ## Deploy demo application to cluster
	@echo -e "$(BLUE)Deploying demo application...$(NC)"
	@kubectl apply -k examples/demo-app/
	@echo -e "$(BLUE)Waiting for pods to be ready...$(NC)"
	@kubectl wait --for=condition=Ready pod -l app=demo-db -n production --timeout=120s || true
	@kubectl wait --for=condition=Ready pod -l app=demo-redis -n production --timeout=60s || true
	@kubectl wait --for=condition=Ready pod -l app=demo-api -n production --timeout=120s || true
	@echo -e "$(GREEN)✓ Demo app deployed$(NC)"
	@kubectl get pods -n production

demo-app-status: ## Show status of demo application
	@echo -e "$(BLUE)Demo Application Status$(NC)"
	@echo "========================"
	@kubectl get pods -n production -o wide
	@echo ""
	@echo -e "$(BLUE)Services:$(NC)"
	@kubectl get svc -n production
	@echo ""
	@echo -e "$(BLUE)Recent Events:$(NC)"
	@kubectl get events -n production --sort-by='.lastTimestamp' | tail -10

demo-incident-crashloop: ## Inject CrashLoopBackOff incident
	@echo -e "$(YELLOW)Injecting CrashLoopBackOff incident...$(NC)"
	@kubectl apply -f examples/incidents/crashloop-missing-env.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-oomkill: ## Inject OOMKilled incident
	@echo -e "$(YELLOW)Injecting OOMKilled incident...$(NC)"
	@kubectl apply -f examples/incidents/oomkill-memory-leak.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-imagepull: ## Inject ImagePullBackOff incident
	@echo -e "$(YELLOW)Injecting ImagePullBackOff incident...$(NC)"
	@kubectl apply -f examples/incidents/imagepull-bad-tag.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-pending: ## Inject Pending pod incident
	@echo -e "$(YELLOW)Injecting Pending pod incident...$(NC)"
	@kubectl apply -f examples/incidents/pending-no-resources.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl describe pod -l app=demo-api -n production$(NC)"

demo-incident-liveness: ## Inject Liveness probe failure incident
	@echo -e "$(YELLOW)Injecting Liveness probe failure...$(NC)"
	@kubectl apply -f examples/incidents/liveness-failure.yaml
	@echo -e "$(GREEN)✓ Incident injected. Run: kubectl get pods -n production -w$(NC)"

demo-incident-reset: ## Reset demo app to healthy state
	@echo -e "$(BLUE)Resetting demo app to healthy state...$(NC)"
	@kubectl apply -f examples/demo-app/demo-api.yaml
	@kubectl rollout restart deployment/demo-api -n production
	@kubectl wait --for=condition=Ready pod -l app=demo-api -n production --timeout=120s
	@echo -e "$(GREEN)✓ Demo app reset to healthy state$(NC)"

demo-k8sgpt-analyze: ## Run K8sGPT analysis on cluster
	@echo -e "$(BLUE)Running K8sGPT analysis...$(NC)"
	@k8sgpt analyze --filter=Pod --namespace=production --explain

demo-k8sgpt-config: ## Configure K8sGPT with Ollama backend
	@echo -e "$(BLUE)Configuring K8sGPT with Ollama...$(NC)"
	@k8sgpt auth remove --backend ollama 2>/dev/null || true
	@k8sgpt auth add --backend ollama --baseurl http://localhost:11434 --model phi3:mini
	@echo -e "$(GREEN)✓ K8sGPT configured$(NC)"

demo-aegis-analyze: ## Run AEGIS analysis on demo-api pod
	@echo -e "$(BLUE)Running AEGIS analysis...$(NC)"
	$(UV) run aegis analyze pod/demo-api --namespace production

demo-shadow-create: ## Create a shadow environment for testing
	@echo -e "$(BLUE)Creating shadow environment...$(NC)"
	@vcluster create shadow-test -n aegis-shadows -f examples/shadow/vcluster-template.yaml --connect=false
	@echo -e "$(GREEN)✓ Shadow environment created$(NC)"

demo-shadow-list: ## List shadow environments
	@echo -e "$(BLUE)Shadow Environments:$(NC)"
	@vcluster list

demo-shadow-delete: ## Delete test shadow environment
	@echo -e "$(YELLOW)Deleting shadow environment...$(NC)"
	@vcluster delete shadow-test -n aegis-shadows
	@echo -e "$(GREEN)✓ Shadow environment deleted$(NC)"

demo-clean: ## Clean up all demo resources
	@echo -e "$(YELLOW)Cleaning up demo resources...$(NC)"
	@kubectl delete namespace production --ignore-not-found=true || true
	@kubectl delete namespace aegis-shadows --ignore-not-found=true || true
	@kubectl delete namespace aegis-system --ignore-not-found=true || true
	@echo -e "$(GREEN)✓ Demo resources cleaned$(NC)"

demo-full: demo-cluster-create demo-app-deploy ## Full demo setup (cluster + app)
	@echo ""
	@echo -e "$(GREEN)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║                    Demo Environment Ready!                   ║$(NC)"
	@echo -e "$(GREEN)╠══════════════════════════════════════════════════════════════╣$(NC)"
	@echo -e "$(GREEN)║  Demo API: http://localhost:30000                            ║$(NC)"
	@echo -e "$(GREEN)║                                                              ║$(NC)"
	@echo -e "$(GREEN)║  Inject an incident:                                         ║$(NC)"
	@echo -e "$(GREEN)║    make demo-incident-crashloop                              ║$(NC)"
	@echo -e "$(GREEN)║    make demo-incident-oomkill                                ║$(NC)"
	@echo -e "$(GREEN)║                                                              ║$(NC)"
	@echo -e "$(GREEN)║  Analyze with AEGIS:                                         ║$(NC)"
	@echo -e "$(GREEN)║    make demo-aegis-analyze                                   ║$(NC)"
	@echo -e "$(GREEN)╚══════════════════════════════════════════════════════════════╝$(NC)"
>>>>>>> af4493e9664b4940d61757df392615e5aaeb514e
