<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=220&text=AEGIS&fontSize=64&fontColor=ffffff&color=0:0b1021,50:0f766e,100:0369a1&animation=twinkling&fontAlignY=38" alt="AEGIS banner" />
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&size=22&pause=1200&color=22D3EE&center=true&vCenter=true&width=900&lines=Autonomous+SRE+Agent+for+Kubernetes;AI-Powered+Incident+Analysis+%2B+Shadow+Verification;Verify+Fixes+Before+Touching+Production" alt="Typing intro" />
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12%2B-0b1021?style=for-the-badge&logo=python&logoColor=FFD43B">
  <img alt="Kubernetes" src="https://img.shields.io/badge/Kubernetes-Operator-0f766e?style=for-the-badge&logo=kubernetes&logoColor=white">
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-Multi--Agent-0369a1?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-GPLv3-111827?style=for-the-badge">
</p>

<p align="center">
  <img src="https://img.icons8.com/3d-fluency/94/python.png" width="54" alt="Python" />
  <img src="https://img.icons8.com/3d-fluency/94/kubernetes.png" width="54" alt="Kubernetes" />
  <img src="https://img.icons8.com/3d-fluency/94/docker.png" width="54" alt="Docker" />
  <img src="https://img.icons8.com/3d-fluency/94/artificial-intelligence.png" width="54" alt="AI" />
  <img src="https://img.icons8.com/3d-fluency/94/combo-chart.png" width="54" alt="Observability" />
  <img src="https://img.icons8.com/3d-fluency/94/security-shield-green.png" width="54" alt="Security" />
</p>

## Objective
AEGIS is designed to become a **reliable autonomous SRE layer** for Kubernetes: detect incidents, analyze root causes with AI, propose remediations, and verify fixes in isolated shadow environments before production changes are applied.

### Goal
- Reduce incident triage and remediation time.
- Prevent risky blind fixes in production.
- Add human approval and security gates in the remediation loop.

## What Is Implemented
- **Kubernetes operator** built with `kopf` for event-driven incident handling.
- **CLI suite** for analysis, incident management, operator control, and shadow lifecycle operations.
- **AI multi-agent workflow** (`RCA -> Solution -> Verifier`) orchestrated with LangGraph.
- **Shadow verification engine** with environment creation, status tracking, verification, and cleanup.
- **Security pipeline hooks** for Trivy, Kubesec, and Falco checks.
- **Observability integration** (Prometheus metrics, structured logging, optional Loki/Grafana links).
- **Quality gates** with Ruff, mypy, pytest, pre-commit, and security checks.

## How It Works
```text
Kubernetes Event
   -> Incident Detection (Kopf handlers)
   -> AI RCA + Fix Proposal (LangGraph agents)
   -> Shadow Environment Creation
   -> Verification + Security Scans
   -> Human Approval
   -> Fix Applied to Production
```

## Build And Run
### 1. Prerequisites
- Python `3.12+`
- `uv`
- Docker
- Kubernetes access (`kubectl` + kubeconfig)

### 2. Setup
```bash
make setup
cp .env.example .env
```

### 3. Install dependencies directly (alternative)
```bash
uv sync --frozen --all-extras
```

### 4. Local quality checks
```bash
make lint
make type-check
make test
make security
```

### 5. Run the CLI
```bash
uv run aegis --help
uv run aegis config
uv run aegis analyze deployment/my-api --namespace default --mock
```

### 6. Run the operator
```bash
uv run aegis operator run --namespace default
# or
uv run aegis-operator --namespace default --dev --verbose
```

## Usage Examples
```bash
# Analyze a resource
uv run aegis analyze pod/nginx-crashloop -n default

# List incidents
uv run aegis incident list --all-namespaces

# Create and verify a shadow environment
uv run aegis shadow create deployment/my-api -n default --wait
uv run aegis shadow verify --ephemeral --app deployment/my-api -n default --duration 45

# Check operator health
uv run aegis operator status
```

## Tools And Stack
| Area | Tools Used |
|---|---|
| Language & Runtime | Python, Typer, AsyncIO |
| Kubernetes Control Plane | Kopf, Kubernetes Python Client, Helm, Kustomize |
| AI / Reasoning | LangGraph, LangChain Core, Ollama, Groq, Gemini |
| Security | Trivy, Kubesec, Falco |
| Observability | Prometheus, OpenTelemetry, Loki, Grafana, structlog |
| Infrastructure | Docker, kind, minikube, vCluster |
| QA / DevEx | Ruff, mypy, pytest, pre-commit, bandit, pip-audit |

## Project Structure
```text
src/aegis/
  agent/           # RCA/solution/verifier agents + graph orchestration
  k8s_operator/    # Kubernetes operator entrypoint + handlers
  shadow/          # Shadow environment lifecycle + verification logic
  security/        # Trivy/Kubesec/Falco integrations
  kubernetes/      # Cluster monitoring and fix application helpers
  observability/   # Metrics, logging, dashboard links
  config/          # Typed settings from environment

deploy/            # Helm, K8s manifests, Docker observability stack
tests/             # Unit, integration, benchmarks
examples/          # Demo apps and incident samples
```

## Contributing
Contribution guidelines are in `CONTRIBUTION.md`.

## License
This project is licensed under the **GNU General Public License v3.0**. See `LICENSE`.
