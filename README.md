# 🛡️ AEGIS - Autonomous SRE Agent with Shadow Verification

[![CI Status](https://github.com/your-org/aegis/workflows/CI/badge.svg)](https://github.com/your-org/aegis/actions)
[![codecov](https://codecov.io/gh/your-org/aegis/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/aegis)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**AEGIS** is an autonomous SRE agent that detects, analyzes, and fixes production incidents using AI-powered reasoning and shadow verification sandboxes.

## 🌟 Key Features

- **Shadow Verification**: Test fixes in ephemeral sandbox environments before production deployment
- **AI-Powered Analysis**: Uses local LLMs (Ollama/vLLM) for intelligent incident diagnosis
- **Multi-Layer Isolation**: vCluster + Kata Containers + gVisor for secure testing
- **Automated Security Testing**: OWASP ZAP, Trivy, and custom exploit generation
- **Full Observability**: Prometheus, Loki, OpenTelemetry integration
- **Kubernetes-Native**: Built as a Kubernetes operator using Kopf

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development Setup](#development-setup)
- [GPU Configuration](#gpu-configuration)
- [Architecture](#architecture)
- [Usage](#usage)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

### For Developers with GPUs (Fastest Path)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/aegis.git
cd aegis

# 2. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Setup development environment
make setup

# 4. Check your GPU
make gpu-check

# 5. Start Ollama and pull models
make run-ollama &
make ollama-pull

# 6. Run the operator locally
make run-operator
```

### For Developers without GPUs (Cloud API Mode)

```bash
# 1-3. Same as above

# 4. Get free API keys (no credit card required)
# Groq: https://console.groq.com/ (fastest, recommended)
# Google Gemini: https://aistudio.google.com/apikey (large context)

# 5. Configure API keys
cat > .env.local << EOF
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_gemini_key_here
EOF

# 6. Run operator with cloud APIs only
export OLLAMA_BASE_URL=none  # Disable local GPU check
make run-operator

# The router will automatically use Groq/Gemini free tiers
# Zero infrastructure cost!
```

## 📦 Prerequisites

### Required Software

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **Python** | 3.12+ | Runtime | [python.org](https://www.python.org/downloads/) |
| **uv** | Latest | Package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker** | 24.0+ | Container runtime | [docker.com](https://docs.docker.com/get-docker/) |
| **kubectl** | 1.28+ | Kubernetes CLI | [kubernetes.io](https://kubernetes.io/docs/tasks/tools/) |
| **Helm** | 3.12+ | K8s package manager | [helm.sh](https://helm.sh/docs/intro/install/) |
| **Ollama** | 0.13+ | Local LLM server | [ollama.com](https://ollama.com/download) |

### GPU Requirements (Optional but Recommended)

**For Local Development (2 teammates):**
- NVIDIA GPU with 8GB+ VRAM
- CUDA 12.0+ drivers
- Docker with NVIDIA Container Toolkit

**For Cloud API Development (1 teammate):**
- No GPU required!
- Free API keys from:
  - **Groq** (fastest, 30 req/min free) - Recommended
  - **Google Gemini** (1M token context, free tier)
  - Optional: OpenAI, Anthropic, DeepSeek for paid fallback

**Tested Configurations:**
- RTX 3060 (12GB) - ✅ Excellent (local Ollama)
- RTX 3070 (8GB) - ✅ Good (quantized models)
- RTX 4060 (8GB) - ✅ Good (quantized models)
- Intel Iris Xe - ✅ Perfect (Groq/Gemini APIs, $0 cost)

### Kubernetes Cluster

**Local Development:**
```bash
# Option 1: k3s (lightweight)
curl -sfL https://get.k3s.io | sh -

# Option 2: minikube
minikube start --cpus=4 --memory=8192 --driver=docker

# Option 3: kind
kind create cluster --config deploy/kind-config.yaml
```

**Production:**
- GKE, EKS, AKS, or any CNCF-certified Kubernetes
- Minimum 3 nodes with 8GB RAM each
- GPU nodes optional but recommended

## 🔧 Installation

### 1. Development Environment

```bash
# Install all dependencies
make install-dev

# Setup pre-commit hooks
make setup-precommit

# Verify installation
make quality
make test-unit
```

### 2. GPU Drivers (if using NVIDIA GPUs)

```bash
# NVIDIA Driver Installation (Ubuntu/Debian)
sudo apt update
sudo apt install -y nvidia-driver-545  # Or latest
sudo reboot

# Verify
nvidia-smi

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### 3. Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended models
ollama pull llama3.1:8b           # Primary model (10GB VRAM)
ollama pull llama3.1:8b-q4_K_M    # Quantized (6GB VRAM)
ollama pull codellama:13b         # Code analysis (14GB VRAM)
ollama pull mistral:7b            # Fallback (8GB VRAM)

# Start Ollama server
ollama serve
```

### 4. Kubernetes Components

```bash
# Install vCluster CLI
curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
chmod +x vcluster && sudo mv vcluster /usr/local/bin/

# Install K8sGPT
curl -LO "https://github.com/k8sgpt-ai/k8sgpt/releases/latest/download/k8sgpt_Linux_x86_64.tar.gz"
tar -xzf k8sgpt_Linux_x86_64.tar.gz
sudo mv k8sgpt /usr/local/bin/

# Configure K8sGPT to use Ollama
k8sgpt auth add --backend ollama --model llama3.1:8b --baseurl http://localhost:11434/v1
```

## 💻 Development Setup

### Project Structure Overview

```
aegis/
├── src/aegis/          # Main source code
├── tests/              # Test suite
├── deploy/             # Deployment manifests
├── docs/               # Documentation
└── scripts/            # Utility scripts
```

### Common Development Commands

```bash
# Code quality
make lint              # Run linter
make format            # Format code
make type-check        # Type checking
make quality           # All quality checks

# Testing
make test              # Run all tests
make test-unit         # Unit tests only
make test-cov          # With coverage report
make test-watch        # Watch mode

# Development
make run-operator      # Run operator locally
make shell             # IPython shell
make docs-serve        # Serve docs at localhost:8000

# Kubernetes
make k8s-setup         # Setup local cluster
make k8s-deploy-dev    # Deploy to dev
make k8s-logs          # Tail operator logs

# Docker
make docker-build      # Build images
make docker-run        # Run in Docker

# GPU
make gpu-check         # Check GPU status
make ollama-pull       # Download models

# Cleanup
make clean             # Remove artifacts
make clean-all         # Deep clean (includes venv)
```

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

```bash
# Install hooks
make setup-precommit

# Run manually on all files
make pre-commit-all

# Bypass hooks (not recommended)
git commit --no-verify
```

**What gets checked:**
- ✅ Ruff linting and formatting
- ✅ Type checking (mypy)
- ✅ Secret scanning (detect-secrets)
- ✅ Security scanning (bandit)
- ✅ YAML/JSON validation
- ✅ Dockerfile linting
- ✅ Conventional commit messages

## 🎮 GPU Configuration

### Team GPU Setup

We support hybrid development with mixed GPU configurations:

```yaml
# config/gpu-profiles/team-gpus.yaml

team_setup:
  teammate_1:  # Strong GPU
    primary_gpu: "local-rtx3060"
    fallback: "cloud-l4"
    
  teammate_2:  # Mid GPU
    primary_gpu: "local-rtx3070"
    fallback: "cloud-t4"
    
  teammate_3:  # No GPU
    primary_gpu: "cloud-t4"
    fallback: "cpu-only"
    openai_api: true
```

### Automatic GPU Detection

The system automatically detects available GPUs:

```python
# Run GPU check
make gpu-check

# Output example:
# ✓ NVIDIA RTX 3060 detected (12GB VRAM)
# ✓ CUDA 12.2 installed
# ✓ Ollama server running
# ✓ Model llama3.1:8b loaded (10GB used)
# → Recommended: Use local GPU for development
```

### Cloud GPU Fallback

If no local GPU is available, the system automatically uses cloud GPUs:

```bash
# Set cloud provider credentials
export GCP_PROJECT_ID="your-project"
export AWS_REGION="us-east-1"

# Deploy cloud GPU instance
make cloud-deploy

# Operator will automatically route LLM requests to cloud
```

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     AEGIS CONTROL PLANE                      │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ LLM Engine  │  │ Agent Core  │  │ Decision    │          │
│  │ (Ollama)    │  │ (LangGraph) │  │ Engine      │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         └────────────────┼────────────────┘                  │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │           AEGIS OPERATOR (Kopf)                      │    │
│  └──────────────────────┬──────────────────────────────┘    │
├──────────────────────────┼───────────────────────────────────┤
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │        SHADOW VERIFICATION LAYER                     │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │    │
│  │  │vCluster │ │  Kata   │ │ gVisor  │ │Ephemeral│   │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

For detailed architecture documentation, see [docs/architecture/overview.md](docs/architecture/overview.md).

## 📖 Usage

### Running the Operator

```bash
# Local development
make run-operator

# In Kubernetes
make k8s-deploy-dev
```

### Creating an Incident

```yaml
# examples/incidents/memory-leak.yaml
apiVersion: aegis.io/v1
kind: Incident
metadata:
  name: api-memory-leak
spec:
  type: performance
  severity: high
  affected:
    namespace: production
    deployment: api-server
  description: "API server memory usage increasing over time"
```

```bash
kubectl apply -f examples/incidents/memory-leak.yaml
```

### Monitoring Resolution

```bash
# Watch incident status
kubectl get incidents -w

# View operator logs
make k8s-logs

# Check shadow environments
kubectl get vclusters -n aegis-shadows
```

## 🧪 Testing

### Test Organization

```
tests/
├── unit/           # Fast, no external dependencies
├── integration/    # Require K8s cluster
├── fixtures/       # Test data and manifests
└── benchmarks/     # Performance tests
```

### Running Tests

```bash
# All tests
make test

# Unit tests only (fast)
make test-unit

# Integration tests (requires K8s)
make test-integration

# With coverage
make test-cov

# GPU tests (requires GPU)
make test-gpu

# Watch mode (development)
make test-watch
```

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_llm_client():
    """Fast unit test"""
    
@pytest.mark.integration
def test_vcluster_creation():
    """Requires K8s cluster"""
    
@pytest.mark.gpu
def test_ollama_inference():
    """Requires GPU"""
    
@pytest.mark.slow
def test_e2e_scenario():
    """Long-running E2E test"""
```

### CI/CD Testing Strategy

```yaml
# Unit tests: Run on every PR (GitHub Actions CPU)
# Integration: Run on main branch (with K8s)
# E2E: Manual or nightly (with cloud GPU)
# GPU tests: Skip in CI (local only)
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. **Fork and clone** the repository
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Make changes** with tests and documentation
4. **Run quality checks**: `make quality`
5. **Run tests**: `make test`
6. **Commit** with conventional commits: `git commit -m "feat: add shadow verification"`
7. **Push** and create a Pull Request

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add shadow verification for SQL injection
fix: correct vCluster cleanup logic
docs: update GPU setup instructions
test: add integration tests for Kata runtime
refactor: simplify LLM routing logic
chore: update dependencies
```

### Code Review Process

- All PRs require at least 1 approval
- CI checks must pass
- Code coverage must not decrease
- Documentation must be updated

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.com/) - Local LLM inference
- [vCluster](https://www.vcluster.com/) - Virtual Kubernetes clusters
- [K8sGPT](https://k8sgpt.ai/) - Kubernetes diagnostics
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- All the amazing open-source tools in our stack

## 📞 Support

- **Documentation**: [aegis-sre.dev](https://aegis-sre.dev)
- **Issues**: [GitHub Issues](https://github.com/your-org/aegis/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/aegis/discussions)
- **Email**: team@aegis-sre.dev

---

**Built with ❤️ by the AEGIS Team**