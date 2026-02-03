# AEGIS - Complete Project Structure

```
aegis/
├── .github/
│   ├── workflows/
│   │   ├── pr-checks.yml              # Lint, type-check, test on PRs
│   │   ├── main-ci.yml                # Build & push images on main
│   │   ├── deploy-staging.yml         # Auto-deploy to staging
│   │   ├── deploy-prod.yml            # Manual production deploy
│   │   ├── security-scan.yml          # Trivy, detect-secrets scan
│   │   └── docs-publish.yml           # MkDocs to GitHub Pages
│   ├── dependabot.yml                 # Auto dependency updates
│   └── CODEOWNERS                     # Code review assignments
│
├── src/
│   └── aegis/
│       ├── __init__.py
│       ├── py.typed                   # PEP 561 marker for type hints
│       │
│       ├── operator/
│       │   ├── __init__.py
│       │   ├── main.py                # Kopf operator entry
│       │   ├── handlers/
│       │   │   ├── __init__.py
│       │   │   ├── incident.py        # Incident CRD handlers
│       │   │   ├── shadow.py          # Shadow environment lifecycle
│       │   │   └── rollback.py        # Automated rollback logic
│       │   ├── crds/
│       │   │   ├── incident.yaml      # CustomResourceDefinition
│       │   │   └── shadow.yaml        # Shadow CRD
│       │   └── reconcilers/
│       │       ├── __init__.py
│       │       └── base.py            # Base reconciler class
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── graph.py               # LangGraph orchestration
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   ├── ollama.py          # Ollama client
│       │   │   ├── vllm.py            # vLLM client
│       │   │   ├── openai.py          # OpenAI fallback
│       │   │   └── router.py          # Smart LLM routing
│       │   ├── analyzer.py            # K8sGPT integration
│       │   ├── fix_generator.py       # Automated fix generation
│       │   └── prompts/
│       │       ├── __init__.py
│       │       ├── system.py          # System prompts
│       │       └── templates.py       # Jinja2 prompt templates
│       │
│       ├── shadow/
│       │   ├── __init__.py
│       │   ├── vcluster.py            # vCluster management
│       │   ├── kata.py                # Kata Containers runtime
│       │   ├── gvisor.py              # gVisor sandbox
│       │   ├── cloner.py              # Workload state cloning
│       │   └── verification.py        # Test orchestration
│       │
│       ├── security/
│       │   ├── __init__.py
│       │   ├── trivy.py               # Vulnerability scanning
│       │   ├── zap.py                 # OWASP ZAP automation
│       │   ├── falco.py               # Falco rules integration
│       │   ├── exploit/
│       │   │   ├── __init__.py
│       │   │   ├── sql_injection.py   # SQL injection PoC generator
│       │   │   ├── jwt_cracker.py     # JWT vulnerability tests
│       │   │   └── sandbox.py         # Safe exploit execution
│       │   └── waf.py                 # WAF rule generation
│       │
│       ├── observability/
│       │   ├── __init__.py
│       │   ├── metrics.py             # Prometheus metrics
│       │   ├── logging.py             # Structured logging (Loki)
│       │   ├── tracing.py             # OpenTelemetry setup
│       │   └── alerts.py              # Alert routing
│       │
│       ├── kubernetes/
│       │   ├── __init__.py
│       │   ├── client.py              # K8s Python client wrapper
│       │   ├── resources.py           # Resource models (Pydantic)
│       │   └── utils.py               # K8s utility functions
│       │
│       ├── testing/
│       │   ├── __init__.py
│       │   ├── load/
│       │   │   ├── __init__.py
│       │   │   ├── locust_tasks.py    # Locust load tests
│       │   │   └── k6_scripts.py      # k6 test generation
│       │   └── chaos.py               # Chaos engineering helpers
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py            # Pydantic settings
│       │   └── gpu_profiles.py        # GPU configurations
│       │
│       └── utils/
│           ├── __init__.py
│           ├── retry.py               # Retry decorators
│           ├── async_helpers.py       # Async utilities
│           └── validation.py          # Input validation
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_llm.py
│   │   ├── test_shadow.py
│   │   └── test_security.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_operator.py
│   │   ├── test_vcluster.py
│   │   └── test_e2e_scenario.py
│   ├── fixtures/
│   │   ├── k8s_manifests/
│   │   │   ├── bad_deployment.yaml
│   │   │   └── vulnerable_app.yaml
│   │   └── mock_data/
│   │       └── llm_responses.json
│   └── benchmarks/
│       └── test_llm_throughput.py     # Performance benchmarks
│
├── deploy/
│   ├── helm/
│   │   └── aegis/
│   │       ├── Chart.yaml
│   │       ├── values.yaml            # Default values
│   │       ├── values-dev.yaml
│   │       ├── values-staging.yaml
│   │       ├── values-prod.yaml
│   │       ├── templates/
│   │       │   ├── operator/
│   │       │   │   ├── deployment.yaml
│   │       │   │   ├── serviceaccount.yaml
│   │       │   │   ├── rbac.yaml
│   │       │   │   └── configmap.yaml
│   │       │   ├── llm/
│   │       │   │   ├── ollama-deployment.yaml
│   │       │   │   ├── gpu-node-selector.yaml
│   │       │   │   └── pvc.yaml
│   │       │   ├── observability/
│   │       │   │   ├── prometheus.yaml
│   │       │   │   ├── loki.yaml
│   │       │   │   └── grafana-dashboards.yaml
│   │       │   ├── security/
│   │       │   │   ├── falco.yaml
│   │       │   │   ├── trivy.yaml
│   │       │   │   └── network-policies.yaml
│   │       │   ├── crds/
│   │       │   │   ├── incident.yaml
│   │       │   │   └── shadow.yaml
│   │       │   └── secrets/
│   │       │       └── sealed-secrets.yaml
│   │       └── crds/
│   │           └── incident-crd.yaml
│   │
│   ├── docker/
│   │   ├── Dockerfile.operator        # Multi-stage operator image
│   │   ├── Dockerfile.ollama          # Custom Ollama with models
│   │   ├── Dockerfile.dev             # Development image
│   │   └── .dockerignore
│   │
│   ├── kustomize/
│   │   ├── base/
│   │   │   ├── kustomization.yaml
│   │   │   └── namespace.yaml
│   │   ├── overlays/
│   │   │   ├── dev/
│   │   │   │   └── kustomization.yaml
│   │   │   ├── staging/
│   │   │   │   └── kustomization.yaml
│   │   │   └── prod/
│   │   │       └── kustomization.yaml
│   │   └── patches/
│   │       └── gpu-patch.yaml
│   │
│   ├── terraform/                     # Optional cloud infrastructure
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── gpu-instances.tf           # Cloud GPU provisioning
│   │   └── kubernetes.tf
│   │
│   └── scripts/
│       ├── setup-cluster.sh           # Local K8s setup
│       ├── install-gpu-drivers.sh     # NVIDIA driver setup
│       ├── deploy-dev.sh              # Quick dev deployment
│       └── seed-models.sh             # Download Ollama models
│
├── docs/
│   ├── index.md                       # Main documentation
│   ├── getting-started.md
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── shadow-verification.md
│   │   └── diagrams/
│   │       └── architecture.png
│   ├── development/
│   │   ├── setup.md
│   │   ├── gpu-development.md
│   │   ├── testing.md
│   │   └── contributing.md
│   ├── deployment/
│   │   ├── local.md
│   │   ├── cloud.md
│   │   └── production.md
│   ├── scenarios/
│   │   ├── bad-commit.md
│   │   ├── sql-injection.md
│   │   └── jwt-vulnerability.md
│   └── api/
│       └── reference.md               # Auto-generated API docs
│
├── scripts/
│   ├── dev/
│   │   ├── setup-venv.sh              # uv venv setup
│   │   ├── run-local.sh               # Run operator locally
│   │   └── port-forward.sh            # K8s port forwarding
│   ├── ci/
│   │   ├── run-tests.sh               # CI test runner
│   │   ├── build-images.sh            # Docker build script
│   │   └── security-scan.sh           # Security scanning
│   └── utils/
│       ├── check-gpu.py               # GPU availability check
│       └── generate-secrets.sh        # Kubernetes secrets generation
│
├── config/
│   ├── gpu-profiles/
│   │   ├── rtx3060.yaml               # 12GB profile
│   │   ├── rtx3070.yaml               # 8GB profile
│   │   └── cloud-l4.yaml              # Cloud GPU profile
│   ├── models/
│   │   ├── ollama-models.yaml         # Model configurations
│   │   └── model-router.yaml          # LLM routing rules
│   └── observability/
│       ├── prometheus-rules.yaml
│       ├── loki-config.yaml
│       └── grafana-dashboards/
│           ├── aegis-overview.json
│           └── shadow-metrics.json
│
├── examples/
│   ├── incidents/
│   │   ├── memory-leak.yaml           # Example incident CRDs
│   │   └── sql-injection.yaml
│   ├── fixes/
│   │   └── rollback-deployment.yaml
│   └── notebooks/
│       ├── llm-testing.ipynb          # LLM prompt development
│       └── scenario-simulation.ipynb  # Test scenario notebooks
│
├── .devcontainer/
│   ├── devcontainer.json              # VSCode devcontainer
│   └── Dockerfile
│
├── .vscode/
│   ├── settings.json                  # Workspace settings
│   ├── launch.json                    # Debug configurations
│   └── extensions.json                # Recommended extensions
│
├── pyproject.toml                     # uv, ruff, mypy, pytest config
├── uv.lock                            # Lock file (auto-generated)
├── .python-version                    # Python version (3.12)
├── .pre-commit-config.yaml            # Pre-commit hooks
├── .secrets.baseline                  # detect-secrets baseline
├── .gitignore
├── .dockerignore
├── .editorconfig                      # Editor consistency
├── mkdocs.yml                         # Documentation config
├── Makefile                           # Common commands
├── README.md                          # Project overview
├── CONTRIBUTING.md                    # Contribution guidelines
├── LICENSE                            # Apache 2.0
└── CHANGELOG.md                       # Version history
```

## File Count Summary
- **Python modules**: ~60 files
- **Tests**: ~20 files
- **K8s manifests**: ~30 files
- **Documentation**: ~15 files
- **Config files**: ~15 files
- **CI/CD workflows**: 6 files
- **Total**: ~150 files

## Key Design Decisions

### 1. **Monorepo Structure**
- Single source of truth
- Shared utilities and types
- Simplified CI/CD

### 2. **Type Safety First**
- `py.typed` marker for library typing
- Pydantic for all data models
- mypy strict mode

### 3. **GPU-Aware Design**
- Profile-based GPU configuration
- Automatic fallback to cloud/CPU
- GPU availability detection in CI

### 4. **Multi-Stage Deployment**
- Kustomize overlays for environments
- Helm values per stage
- Sealed Secrets for GitOps

### 5. **Testing Strategy**
- Unit tests run on every PR
- Integration tests on main branch
- E2E tests manual/nightly
- Load tests only in staging/prod

### 6. **Documentation**
- MkDocs Material (best for technical docs)
- Auto-generated API reference
- Jupyter notebooks for examples