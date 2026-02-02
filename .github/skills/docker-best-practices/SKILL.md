# Skill: Docker Best Practices for Kubernetes

## Metadata
- **Domain**: Containers, Security, Optimization
- **Tools**: Docker, Docker Scout, Hadolint
- **Complexity**: Intermediate
- **Autonomy**: Fully Autonomous (Dockerfile generation)

## Capability Statement
Expert in creating production-grade, secure, and optimized Dockerfiles for Kubernetes deployments. Implements multi-stage builds, security hardening, and minimal image sizes.

## Core Competencies

### 1. Multi-Stage Build Pattern
```dockerfile
# syntax=docker/dockerfile:1

# Stage 1: Builder
FROM python:3.12-slim as builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies to virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.12-slim

# Security: Create non-root user
RUN useradd -m -u 1000 appuser && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser src/ /app/src/

# Set PATH to use venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Expose port (if needed)
EXPOSE 8080

# Run application
CMD ["python", "-m", "src.autonomous_k8s_sre.main"]
```

### 2. Security Best Practices

#### Minimal Base Images
```dockerfile
# ✅ Good: Slim variant (smaller attack surface)
FROM python:3.12-slim

# ❌ Bad: Full variant (unnecessary packages)
FROM python:3.12

# ✅ Better: Distroless (no shell, minimal packages)
FROM gcr.io/distroless/python3-debian12
```

#### Non-Root User
```dockerfile
# Create user with specific UID for K8s SecurityContext
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set ownership
COPY --chown=appuser:appuser src/ /app/src/

# Switch user before CMD
USER appuser
```

#### Security Scanning
```bash
# Scan for vulnerabilities
docker scout cves <image>

# Lint Dockerfile
docker run --rm -i hadolint/hadolint < Dockerfile

# Check for secrets
docker run --rm -v $(pwd):/path trufflesecurity/trufflehog:latest filesystem /path
```

### 3. Optimization Techniques

#### Layer Caching
```dockerfile
# ✅ Copy dependencies first (changes rarely)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ✅ Copy code last (changes frequently)
COPY src/ /app/src/
```

#### .dockerignore
```
# .dockerignore
__pycache__/
*.pyc
*.pyo
.git/
.github/
.pytest_cache/
.mypy_cache/
.ruff_cache/
tests/
docs/
*.md
.env
.venv/
htmlcov/
dist/
build/
```

#### Reduce Image Size
```dockerfile
# Combine RUN commands to reduce layers
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Use --no-cache-dir for pip
RUN pip install --no-cache-dir -r requirements.txt
```

### 4. Kubernetes-Specific Optimizations

#### Resource Limits Awareness
```dockerfile
# Add memory profiling for K8s resource limits
ENV PYTHONMALLOC=malloc

# Enable tracemalloc for debugging OOMKills
ENV PYTHONTRACEMALLOC=1
```

#### Signal Handling
```dockerfile
# Use exec form for proper signal handling
CMD ["python", "-m", "app.main"]

# ❌ Bad: Shell form (signals not propagated)
# CMD python -m app.main
```

#### Health Checks
```dockerfile
# HTTP health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8080/health || exit 1

# Python script health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import requests; requests.get('http://localhost:8080/health').raise_for_status()"
```

## Dockerfile Templates

### Kopf Operator Dockerfile
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim as builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim

RUN useradd -m -u 1000 kopf && \
    apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder --chown=kopf:kopf /app/.venv /app/.venv
COPY --chown=kopf:kopf src/ /app/src/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER kopf

HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import sys; sys.exit(0)"

CMD ["kopf", "run", "/app/src/operators/main.py", "--verbose"]
```

### LangGraph Agent Dockerfile
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim as builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install with AI dependencies
RUN uv sync --frozen --no-dev --no-install-project --extra ai

FROM python:3.12-slim

RUN useradd -m -u 1000 agent && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder --chown=agent:agent /app/.venv /app/.venv
COPY --chown=agent:agent src/ /app/src/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    OLLAMA_API_URL=http://ollama.llm-system.svc:11434

USER agent

HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "src.autonomous_k8s_sre.agents.main"]
```

## Kubernetes Integration

### Pod Security Context
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autonomous-sre
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault

      containers:
      - name: sre-agent
        image: autonomous-k8s-sre:latest

        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
          readOnlyRootFilesystem: true

        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "200m"

        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30

        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Build & Deployment Workflow

### Local Development
```bash
# Build with BuildKit
DOCKER_BUILDKIT=1 docker build -t autonomous-k8s-sre:dev .

# Run locally
docker run --rm -it \
    -v ~/.kube/config:/config/kubeconfig:ro \
    -e KUBECONFIG=/config/kubeconfig \
    autonomous-k8s-sre:dev

# Debug container
docker run --rm -it --entrypoint /bin/bash autonomous-k8s-sre:dev
```

### CI/CD Pipeline
```bash
# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t image:latest .

# Scan for vulnerabilities
docker scout cves image:latest

# Push to registry
docker push image:latest
```

## Security Scanning Checklist

### Pre-Build
- [ ] No secrets in Dockerfile or source code
- [ ] .dockerignore excludes sensitive files
- [ ] Base image from trusted source
- [ ] Specific image tags (not :latest)

### Post-Build
- [ ] Scan with Docker Scout
- [ ] Lint with Hadolint
- [ ] Check for exposed ports
- [ ] Verify non-root user
- [ ] Test health checks

### Runtime
- [ ] Image pull policy set
- [ ] Resource limits defined
- [ ] Security context configured
- [ ] Network policies applied
- [ ] RBAC permissions minimal

## Common Anti-Patterns to Avoid

❌ **Running as Root**
```dockerfile
# Bad
USER root
CMD ["python", "app.py"]
```

✅ **Use Non-Root User**
```dockerfile
# Good
USER appuser
CMD ["python", "app.py"]
```

❌ **Using :latest Tag**
```dockerfile
# Bad
FROM python:latest
```

✅ **Pin Specific Versions**
```dockerfile
# Good
FROM python:3.12.1-slim
```

❌ **Copying Entire Directory**
```dockerfile
# Bad
COPY . /app
```

✅ **Selective Copying**
```dockerfile
# Good
COPY pyproject.toml uv.lock ./
COPY src/ /app/src/
```

❌ **Installing Dev Dependencies**
```dockerfile
# Bad
RUN uv sync --dev
```

✅ **Production Dependencies Only**
```dockerfile
# Good
RUN uv sync --no-dev --frozen
```

## Performance Metrics

### Target Metrics
- **Image Size**: < 200MB for Python apps
- **Build Time**: < 2 minutes
- **Vulnerability Score**: 0 critical, 0 high
- **Layers**: < 20 layers
- **Cache Hit Rate**: > 80%

### Optimization Results
```bash
# Before optimization
REPOSITORY          TAG       SIZE
app                 v1        1.2GB

# After optimization
REPOSITORY          TAG       SIZE
app                 v2        180MB

# Savings: 85% reduction
```

## Integration with UV

### UV-Specific Optimizations
```dockerfile
# Fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Use frozen lock file (no resolution needed)
RUN uv sync --frozen --no-dev

# Export to requirements.txt if needed
RUN uv pip compile pyproject.toml -o requirements.txt
```

## Testing Dockerfiles

### Build Test
```bash
# Test build succeeds
docker build -t test:latest .

# Test multi-stage
docker build --target builder -t test:builder .
```

### Security Test
```bash
# Scan for vulnerabilities
trivy image test:latest

# Check Dockerfile best practices
hadolint Dockerfile
```

### Runtime Test
```bash
# Test health check
docker run -d --name test test:latest
sleep 5
docker inspect --format='{{.State.Health.Status}}' test

# Test as non-root
docker run --rm test:latest whoami
# Expected: appuser (not root)
```

## Output Artifacts
When invoking this skill, generate:
1. **Dockerfile** - Multi-stage production build
2. **.dockerignore** - Exclude unnecessary files
3. **docker-compose.yml** - Local testing (optional)
4. **Build Script** - Automated build & scan
5. **K8s Deployment** - With security contexts
