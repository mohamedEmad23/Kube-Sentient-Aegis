# AEGIS Development Environment Setup

This guide helps new team members set up their development environment for the AEGIS project. Following these steps ensures consistent code quality across the team.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Pre-commit Hooks](#pre-commit-hooks)
4. [Tool Reference](#tool-reference)
5. [Troubleshooting](#troubleshooting)
6. [Bypassing Hooks](#bypassing-hooks)

---

## Prerequisites

### Required Software

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| Python | 3.12+ | Runtime environment | [python.org](https://python.org) |
| Git | 2.30+ | Version control | `brew install git` or `apt install git` |
| Docker | 24.0+ | Container runtime | [docker.com](https://docker.com) |

### Recommended (Optional)

| Tool | Purpose | Installation |
|------|---------|--------------|
| hadolint | Dockerfile linting | `brew install hadolint` |
| shellcheck | Shell script linting | `brew install shellcheck` |
| kubectl | Kubernetes CLI | `brew install kubectl` |
| kind | Local K8s clusters | `brew install kind` |

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/mohamedEmad23/Kube-Sentient-Aegis.git
cd Kube-Sentient-Aegis
```

### 2. Create Virtual Environment

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Or using standard Python
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Install Pre-commit Hooks

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

### 4. Verify Installation

```bash
pre-commit run --all-files
```

All hooks should pass. If any fail, see [Troubleshooting](#troubleshooting).

---

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality. Here's what each hook does and why it matters:

### Code Quality Hooks

| Hook | Purpose | Business Impact |
|------|---------|-----------------|
| **ruff** | Python linting & formatting | Catches bugs before code review, ensures consistent style |
| **mypy** | Type checking | Prevents runtime type errors, improves code reliability |
| **bandit** | Security scanning | Identifies security vulnerabilities before deployment |

### Security Hooks

| Hook | Purpose | Business Impact |
|------|---------|-----------------|
| **detect-secrets** | Prevents credential leaks | Protects customer data and company reputation |
| **detect-private-key** | Blocks private key commits | Prevents unauthorized access to systems |

### Infrastructure Hooks

| Hook | Purpose | Business Impact |
|------|---------|-----------------|
| **hadolint** | Dockerfile best practices | Ensures reliable container builds |
| **shellcheck** | Shell script validation | Prevents deployment script failures |
| **check-yaml** | YAML syntax validation | Catches K8s manifest errors early |

### Commit Standards

| Hook | Purpose | Business Impact |
|------|---------|-----------------|
| **commitizen** | Enforces commit message format | Enables automated changelog generation |
| **no-commit-to-branch** | Protects main branches | Prevents accidental direct commits |

---

## Tool Reference

### Ruff (Python Linting)

Ruff replaces multiple tools (black, isort, flake8, pylint) with a single fast linter.

```bash
# Run manually
ruff check src/
ruff format src/

# Auto-fix issues
ruff check --fix src/
```

**Common Suppressions:**

```python
# Suppress single line
x = 1  # noqa: E501 - Line length acceptable for readability

# Suppress entire file (at top)
# ruff: noqa: A005 - Module name shadows stdlib intentionally
```

### Mypy (Type Checking)

Ensures type annotations are correct and consistent.

```bash
# Run manually
mypy src/
```

**Configuration:** See `pyproject.toml` under `[tool.mypy]`

### Hadolint (Dockerfile Linting)

Validates Dockerfiles against best practices.

```bash
# Using local binary
hadolint deploy/docker/Dockerfile

# Using Docker (if binary not installed)
docker run --rm -i hadolint/hadolint < deploy/docker/Dockerfile

# Using project script (auto-detects mode)
./scripts/hadolint-check.sh deploy/docker/Dockerfile
```

**Installation:**
- macOS: `brew install hadolint`
- Linux: Download from [GitHub Releases](https://github.com/hadolint/hadolint/releases)
- Docker: Automatically used as fallback

### Detect-Secrets

Scans for accidentally committed credentials.

```bash
# Scan files
detect-secrets scan

# Update baseline (after reviewing false positives)
detect-secrets scan --baseline .secrets.baseline
```

**Marking False Positives:**

```yaml
# In YAML files
password: "example"  # pragma: allowlist secret - Demo value for documentation

# In Python files
API_KEY = "test-key"  # pragma: allowlist secret
```

---

## Troubleshooting

### "ruff" fails with TRY301

**Cause:** Ruff flags `raise` inside helper functions as potentially hiding exceptions.

**Solution:** For CLI control flow (like `typer.Exit`), add suppression with justification:

```python
# noqa: TRY301 - typer.Exit is CLI control flow, not error handling
raise typer.Exit(code=1)
```

### "mypy" fails with type errors

**Cause:** Missing type annotations or incompatible types.

**Solutions:**
1. Add missing type hints
2. Use `# type: ignore[error-code]` for external libraries
3. Check `pyproject.toml` for ignored imports

### "detect-secrets" false positives

**Cause:** Demo credentials or example values flagged as secrets.

**Solution:** Add pragma with justification:

```yaml
password: "demo123"  # pragma: allowlist secret - Demo credentials for local testing
```

**Important:** Never suppress real secrets. Only demo/example values.

### "hadolint" not found

**Cause:** hadolint binary not installed.

**Solutions:**
1. Install locally: `brew install hadolint`
2. Ensure Docker is running (automatic fallback)
3. Check error message for installation instructions

### Pre-commit hangs on mypy

**Cause:** mypy analyzing large codebase without caching.

**Solution:** First run may be slow. Subsequent runs use cache.

```bash
# Clear cache if corrupted
rm -rf .mypy_cache
```

---

## Bypassing Hooks

### When It's Acceptable

- **Emergency hotfix** with immediate follow-up to fix issues
- **WIP commits** on feature branches (squash before merge)
- **Documentation-only** changes with known issues

### When It's NOT Acceptable

- Production deployments
- Commits to `main`, `develop`, or `staging`
- Security-related changes
- Any code that will be reviewed

### How to Bypass

```bash
# Skip all hooks (use sparingly)
git commit --no-verify -m "WIP: temporary commit"

# Skip specific hooks
SKIP=mypy git commit -m "feat: quick fix"

# Skip multiple hooks
SKIP=mypy,ruff git commit -m "WIP: work in progress"
```

**Remember:** Bypassed commits must be fixed before merging to main branches.

---

## CI/CD Integration

Pre-commit hooks also run in CI/CD pipelines via GitHub Actions. The configuration mirrors local development:

```yaml
# .github/workflows/ci.yml
- name: Run pre-commit
  uses: pre-commit/action@v3.0.0
```

### CI-Specific Considerations

- **Docker-based linting**: CI uses Docker for hadolint (no local binary)
- **Caching**: Mypy and ruff caches are preserved between runs
- **Secrets baseline**: Must be committed and up-to-date

---

## Getting Help

- **Slack:** `#aegis-dev`
- **Documentation:** [docs/](./docs/)
- **Issues:** [GitHub Issues](https://github.com/mohamedEmad23/Kube-Sentient-Aegis/issues)

---

*Last updated: January 2026*
