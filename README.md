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

## 🚀 Quick Start for Team Members

> **👥 For Data Scientists & Security Engineers** - Complete setup in one command

### One-Command Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/aegis.git
cd aegis

# 2. Ensure Python 3.12+ is installed
python3 --version  # Must be 3.12 or higher

# 3. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 4. Run the master setup command (installs everything)
make setup
```

✅ This single command does everything:

- ✓ Installs all Python dependencies (production + development)
- ✓ Creates `.env` file from template
- ✓ Installs pre-commit git hooks
- ✓ Detects your GPU automatically
- ✓ Recommends optimal Ollama models for your VRAM
- ✓ Verifies everything is working

## 🎯 Quick Demo (5 minutes)

### One-Command Demo (Recommended)

```bash
# 1. Start observability stack
docker compose -f deploy/docker/docker-compose.yaml up -d

# 2. Create a local Kind cluster and deploy the demo app
./scripts/demo-setup.sh

# 3. Analyze a resource with mock data (no cluster required)
aegis analyze pod/demo-nginx --namespace default --mock

# 4. View results
# - Prometheus: http://localhost:9090
# - Grafana:    http://localhost:3000 (admin / aegis123)

# 5. Optional: create a real incident and analyze it
kubectl apply -f examples/incidents/crashloop-missing-env.yaml
aegis analyze pod/nginx-crashloop --namespace default
```

### After Setup: Check Your GPU

```bash
# Auto-detect GPU and get recommendations
make gpu-check

# Output example (8GB VRAM):
# NVIDIA GPU detected: RTX 3070
# Recommended models: llama3.2:3b, phi3:mini, qwen2:7b
```

### For GPU Users: Pull Your Models

```bash
# Automatically pulls the best model for your GPU VRAM
make ollama-pull

# Or manually pull specific models
ollama pull llama3.2:3b
ollama pull phi3:mini
ollama pull tinyllama:1b
```

### For CPU-Only Users: Use Free Cloud APIs

```bash
# Get free API keys (no credit card required, ever):
# Groq: https://console.groq.com/keys (fastest, 30 req/min free)
# Google Gemini: https://aistudio.google.com/apikey (1M token context)

# Add to .env
GROQ_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Run - the router will automatically use them!
make run-operator
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

## 📂 Project Structure & Key Files

```
aegis/
├── .github/                      # GitHub Actions CI/CD
├── .vscode/                      # VS Code settings (shared for team)
├── config/
│   ├── gpu-profiles/
│   │   └── team-gpus.yaml        # 👈 Team GPU configuration
│   └── models/
├── deploy/
│   ├── docker/                   # Docker images & compose
│   ├── helm/                     # Kubernetes Helm charts
│   ├── kustomize/                # Kustomize overlays (dev/staging/prod)
│   └── terraform/                # Infrastructure as Code
├── docs/                         # 📖 Documentation
│   ├── architecture/             # Design & architecture
│   ├── deployment/               # Deployment guides
│   └── development/              # Developer guides
├── src/aegis/                    # 🔥 Main source code
│   ├── agent/                    # AI agent logic
│   ├── cli.py                    # Command-line interface
│   ├── config/                   # Configuration management
│   ├── kubernetes/               # K8s operators
│   ├── observability/            # Logging & metrics
│   ├── operator/                 # K8s operator
│   ├── security/                 # Security scanning
│   └── utils/                    # Utilities
├── tests/                        # 🧪 Test suite
│   ├── unit/                     # Unit tests (fast)
│   ├── integration/              # Integration tests (K8s)
│   └── fixtures/                 # Test data
├── .editorconfig                 # Editor configuration
├── .env.example                  # Environment variables template
├── .pre-commit-config.yaml       # ⚙️ Git hooks configuration
├── .secrets.baseline             # Secrets scanning baseline
├── Makefile                      # 📜 Development commands (see below)
├── pyproject.toml                # Python project config
└── README.md                     # This file
```

### Important Files You'll Use

| File | Purpose | Edit? |
|------|---------|-------|
| [Makefile](Makefile) | All development commands (`make setup`, `make test`, etc.) | ❌ No |
| [.env.example](.env.example) | Template for environment variables | ℹ️ Only to add new vars |
| `.env` | Your local config (auto-created, don't commit!) | ✅ Yes |
| [pyproject.toml](pyproject.toml) | Python dependencies & config | ❌ Ask Mohammed |
| [.pre-commit-config.yaml](.pre-commit-config.yaml) | Git hooks config | ❌ No |
| [config/gpu-profiles/team-gpus.yaml](config/gpu-profiles/team-gpus.yaml) | Team GPU info | ✅ Update yours |
| [src/aegis/](src/aegis/) | **Main code** | ✅ Yes |
| [tests/](tests/) | **Test files** | ✅ Yes |

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

## 🪝 Pre-Commit Hooks & Quality Checks

### What Are Pre-Commit Hooks?

Git hooks automatically run quality checks **before each commit**. This prevents bad code from entering the repository.

### Quality Checks Explained

| Check | Tool | What It Does | Auto-Fixes? |
|-------|------|-------------|-----------|
| Trailing whitespace | pre-commit | Removes extra spaces | ✅ Yes |
| Missing newlines | pre-commit | Adds newlines at EOF | ✅ Yes |
| YAML/JSON syntax | pre-commit | Validates format | ❌ Report only |
| Python imports | ruff | Sorts imports correctly | ✅ Yes |
| Code formatting | ruff-format | Formats code style | ✅ Yes |
| Linting | ruff | Finds bugs & code issues | ✅ Mostly |
| Type checking | mypy | Checks type annotations | ❌ Report only |
| Secrets scanning | detect-secrets | Finds hardcoded secrets | ❌ Report only |
| Security issues | bandit | Finds security flaws | ❌ Report only |

### Most Common Issue: Import Not Sorted

```bash
# ❌ BAD - Hook will fail
from z_module import something
from a_module import other

# ✅ GOOD - After make format
from a_module import other
from z_module import something

# Fix: Just run this before committing
make format
git add .
git commit -m "Your message"
```

### Pre-Commit Hook Protection

**Protected Branches** (require PR, no direct commits):

- ✅ `main` - Production code only

**Allowed Branches** (direct commits OK, use for development):

- ✓ `feature/*` - New features
- ✓ `fix/*` - Bug fixes
- ✓ `docs/*` - Documentation
- ✓ `develop` - Development branch
- ✓ `staging` - Staging branch

### Troubleshooting Pre-Commit Issues

```bash
# "Pre-commit hook failed"
# Solution: The error message tells you what's wrong

# Most common fix:
make format  # Auto-fixes formatting
make lint    # Shows remaining issues
git add .
git commit -m "Your message"

# "Secret detected"
# NEVER commit secrets! Use environment variables:
# In .env (git-ignored):
GROQ_API_KEY=gsk_xxxxx

# In code:
api_key = os.getenv("GROQ_API_KEY")

# "Type checking failed (mypy)"
# Add type annotations to fix:
def process_data(data: dict) -> str:  # Add types
    return str(data)

# Skip hooks only for emergency hotfixes
git commit --no-verify -m "Critical hotfix"
```

## 📜 Command Reference - All Development Commands

```bash
# ============== SETUP (One-time) ==============
make setup              # Master setup command (installs everything!)
make install            # Install production dependencies only
make install-dev        # Install all dependencies (dev + prod)

# ============== CODE QUALITY ==============
make format             # Auto-format all Python code
make lint               # Run linter to find issues
make type-check         # Type checking with mypy
make security           # Security scanning (bandit, safety)
make check-all          # Run format + lint + type-check + security

# ============== TESTING ==============
make test               # Run all tests
make test-unit          # Unit tests only (fast)
make test-cov           # Tests with coverage report
make test-integration   # Integration tests (requires K8s)
make test-watch         # Watch mode (auto-rerun on changes)

# ============== RUNNING ==============
make run                # Run operator locally
make run-dev            # Run operator in dev mode (auto-reload)
make shell              # Interactive Python shell with project loaded
make repl               # IPython shell

# ============== GPU & OLLAMA ==============
make gpu-check          # Auto-detect GPU and recommend models
make ollama-check       # Check Ollama installation
make ollama-pull        # Pull recommended model for your GPU
make ollama-start       # Start Ollama server

# ============== DOCKER & KUBERNETES ==============
make docker-build       # Build Docker image
make docker-push        # Push to registry
make k8s-check          # Verify K8s cluster connection
make k8s-crds           # Install CRDs
make helm-lint          # Lint Helm charts

# ============== DOCUMENTATION ==============
make docs               # Build documentation
make docs-serve         # Serve docs at http://localhost:8000

# ============== BUILD & RELEASE ==============
make build              # Build distribution packages
make publish            # Publish to PyPI

# ============== CLEANUP ==============
make clean              # Clean build artifacts
make clean-all          # Deep clean (removes venv too)

# ============== INFO ==============
make version            # Show project version
make info               # Show project info
make help               # Display all commands
```

### Quick Examples

```bash
# Start developing a new feature
git checkout -b feature/my-feature
make format              # Auto-format code
make check-all           # Run all quality checks
git commit -m "feat: my feature"
git push origin feature/my-feature
# → Create PR on GitHub

# Before committing (critical!)
make format              # Auto-format
make lint                # Find issues
make type-check          # Check types
make test                # Run tests
# Then: git add . && git commit

# Test your changes
make test                # All tests
make test-unit           # Fast unit tests
make test-cov            # With coverage

# Work with your GPU
make gpu-check           # What GPU do I have?
make ollama-pull         # Download model
make run                 # Run the operator

# Clean up
make clean               # Remove artifacts
```

## 🔄 Development Workflow (Required Reading)

⚠️ **IMPORTANT: All team members MUST follow this workflow**

### 1️⃣ Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create your feature branch (use descriptive names)
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
# or
git checkout -b docs/documentation-update
```

### 2️⃣ Make Your Changes

```bash
# Edit files in VS Code
# Write code following Python conventions
```

### 3️⃣ Format & Lint Before Committing (CRITICAL!)

```bash
# Auto-format code (fixes whitespace, imports, line endings)
make format

# Run linter to check code quality
make lint

# Type checking
make type-check

# Or run all quality checks in one go
make check-all
```

### 4️⃣ Commit Your Changes

```bash
git add .
git commit -m "Description of your changes"
```

⚠️ **Pre-commit hooks will automatically run and check:**

- ✓ Python code formatting (ruff)
- ✓ Import sorting (ruff)
- ✓ Type annotations (mypy)
- ✓ Security vulnerabilities (bandit, detect-secrets)
- ✓ Whitespace & line endings (auto-fixed)

**If a hook fails:**

- It will tell you what's wrong
- Most issues are auto-fixed by ruff
- Just run `git add .` and `git commit` again

**Common errors and fixes:**

```bash
# Error: "Type checking failed"
# Fix: Add type annotations, then re-commit
git add .
git commit -m "Your message"

# Error: "Secrets detected"
# Fix: NEVER commit secrets! Use .env instead
# Bad: API_KEY = "sk-123456789"
# Good: API_KEY = os.getenv("API_KEY")
```

### 5️⃣ Push to Remote

```bash
git push origin feature/your-feature-name
```

### 6️⃣ Create a Pull Request (PR)

On GitHub:

1. Click "New Pull Request"
2. Select `main` as base, your branch as compare
3. Add description of your changes
4. Request review from teammates
5. Wait for CI/CD checks and approval

### 7️⃣ After Approval: Merge to Main

Once approved and all checks pass, merge your PR to `main`.

⚠️ **YOU CANNOT COMMIT DIRECTLY TO `main` BRANCH** - This is protected. Always create a PR first.

### Emergency Hotfix Only

```bash
# Only for critical production fixes
git commit --no-verify -m "Critical hotfix: [description]"

# Must create a PR immediately after
```

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

## ⚠️ Important Information for Team Members

### GPU Configuration for Your Team

| Role | GPU | VRAM | Recommended Model | Run This |
|------|-----|------|-------------------|----------|
| Data Scientist #1 | Unknown | 8GB | llama3.2:3b, phi3:mini | `make gpu-check` |
| Data Scientist #2 | Unknown | 6GB | tinyllama:1b, phi3:mini | `make gpu-check` |
| Security Engineer | NVIDIA | Unknown | ? | `make gpu-check` |
| Lead | Intel Iris Xe | N/A | CPU-only / Cloud APIs | Use Groq/Gemini |

**Your GPU will be auto-detected.** Just run `make gpu-check` and follow the instructions!

### Automatic GPU Detection

The system automatically detects your GPU and recommends models:

```bash
make gpu-check

# Output if you have NVIDIA GPU:
# ✓ NVIDIA RTX 3070 detected
# ✓ Available VRAM: 8GB
# ✓ Recommended models: llama3.2:3b, phi3:mini

# Output if no GPU:
# ✓ No NVIDIA GPU detected
# ✓ Options: Use CPU-only or cloud APIs (Groq, Gemini)
```

### No GPU? Use Free Cloud APIs

**Zero cost, no credit card required:**

1. **Groq** (Recommended - fastest)
   - Get key: <https://console.groq.com/keys>
   - Free tier: 30 requests per minute
   - No credit card needed

2. **Google Gemini** (Large context)
   - Get key: <https://aistudio.google.com/apikey>
   - Free tier: 1M tokens per month
   - No credit card needed

3. **Add to your .env:**

   ```bash
   GROQ_API_KEY=gsk_xxxxx
   GOOGLE_API_KEY=xxxxx
   ```

4. **Run - it automatically uses them!**

   ```bash
   make run
   ```

### Troubleshooting Setup

```bash
# "make: command not found"
sudo apt-get install build-essential

# "uv: command not found"
source $HOME/.cargo/env

# "No module named 'aegis'"
source .venv/bin/activate

# "NVIDIA GPU not detected"
# Install NVIDIA drivers first:
sudo apt-get install nvidia-driver-545

# Pre-commit hook keeps failing?
make format       # Auto-fix formatting
make lint         # Check issues
git add .
git commit -m "Your message"
```

### What's Git Pre-Commit?

- ✅ Automatic code quality checks before each commit
- ✅ Prevents bad code from entering the repository
- ✅ Saves time in code reviews
- ⚠️ Main branch is protected (no direct commits)
- ✓ All changes must go through Pull Requests

### GitHub Workflow Summary

1. **Create branch** → `git checkout -b feature/your-feature`
2. **Make changes** → Edit files
3. **Format & lint** → `make format && make check-all`
4. **Commit** → `git commit -m "description"`
5. **Push** → `git push origin feature/your-feature`
6. **Create PR** → Click "New Pull Request" on GitHub
7. **Wait for review** → Get approval
8. **Merge** → Merge to `main`

⚠️ **You cannot commit directly to `main`** - Always use Pull Requests.

## 🤝 Contributing Guidelines

### Before Contributing

1. Read the [Development Workflow](#-development-workflow) section above
2. Run `make setup` to ensure everything is installed
3. Join the team communication channels

### Development Workflow Overview

**The Golden Rules:**

1. ✅ Create a feature branch (never commit to `main`)
2. ✅ Run `make format` and `make check-all` before committing
3. ✅ Pre-commit hooks will validate your code
4. ✅ Create a Pull Request for code review
5. ✅ Get approval before merging

### Step-by-Step for Your First Contribution

```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make your changes
# Edit files in src/aegis/ or tests/

# 3. Format & check everything
make format       # Auto-fixes code style
make check-all    # Lint, type-check, security

# 4. Commit with a clear message
git add .
git commit -m "feat: add your feature"
# Hooks will run automatically!

# 5. Push to remote
git push origin feature/your-feature

# 6. On GitHub: Create Pull Request
# - Describe what you changed
# - Link related issues
# - Request review from teammates

# 7. After approval: Merge to main
```

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature                    # New feature
fix: correct a bug                       # Bug fix
docs: update documentation               # Doc changes
test: add test for feature               # Test changes
refactor: improve code structure         # Code refactoring
chore: update dependencies               # Maintenance
perf: improve performance                # Performance improvement
```

Examples:

```bash
git commit -m "feat: add GPU auto-detection"
git commit -m "fix: correct type annotation in gpu.py"
git commit -m "docs: add GPU setup guide"
git commit -m "test: add test for Ollama integration"
```

### Code Review Process

1. **Create PR** with clear title and description
2. **Wait for CI checks** (automated quality checks)
3. **Assign reviewers** (teammates)
4. **Address feedback** if any
5. **Get approval** (at least 1 reviewer)
6. **Merge to main**

### Testing Requirements

```bash
# Before creating PR, run:
make test          # All tests must pass
make test-cov      # Coverage check
make check-all     # All quality checks
```

**If tests fail:**

```bash
# Fix the issues
# Then re-run tests
make test

# Once passing, commit and push
git add .
git commit -m "fix: address test failures"
git push origin feature/your-feature
```

### When You're Stuck

1. **Check the logs**: `make run` shows detailed error messages
2. **Run tests**: `make test-unit` for fast feedback
3. **Ask teammates**: Use GitHub Issues or team chat
4. **Read docs**: Check [docs/](docs/) folder

### Code Quality Standards

All code must:

- ✅ Pass `make format` (code formatting)
- ✅ Pass `make lint` (code quality)
- ✅ Pass `make type-check` (type safety)
- ✅ Pass `make security` (security scanning)
- ✅ Have tests (`make test`)
- ✅ Have documentation in docstrings

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.com/) - Local LLM inference
- [vCluster](https://www.vcluster.com/) - Virtual Kubernetes clusters
- [K8sGPT](https://k8sgpt.ai/) - Kubernetes diagnostics
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- All the amazing open-source tools in our stack

## 📞 Getting Help

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `make: command not found` | Make not installed | `sudo apt-get install build-essential` |
| `uv: command not found` | uv not in PATH | `source $HOME/.cargo/env` |
| `No module named 'aegis'` | venv not activated | `source .venv/bin/activate` |
| Pre-commit hook fails | Code formatting issue | `make format && git add . && git commit` |
| NVIDIA GPU not detected | Drivers missing | Install NVIDIA drivers + CUDA |
| Import sorting error | Imports not sorted | Run `make format` |
| Type checking error | Missing type annotations | Add type hints to functions |

### Support Channels

- 📖 **Documentation**: [docs/](docs/) folder
- 🐛 **Found a bug?**: Create [GitHub Issue](https://github.com/your-org/aegis/issues)
- 💬 **Questions?**: Use GitHub Discussions
- 📧 **Email**: <team@aegis-sre.dev>

### For Specific Help

**Setup Issues:**
→ Check [Troubleshooting Setup](#troubleshooting-setup) section above

**Pre-Commit Errors:**
→ Check [Pre-Commit Hooks & Quality Checks](#-pre-commit-hooks--quality-checks) section

**GPU Problems:**
→ Run `make gpu-check` for automatic diagnostics

**Test Failures:**
→ Run `make test-unit` for detailed error messages

### Quick Checklist Before Asking for Help

- [ ] I ran `make setup` successfully
- [ ] I ran `make gpu-check` and understood my GPU
- [ ] I ran `make format` on my changes
- [ ] I ran `make check-all` and all checks pass
- [ ] I read the relevant documentation section
- [ ] I checked existing GitHub Issues

---

**Built with ❤️ by the AEGIS Team**
