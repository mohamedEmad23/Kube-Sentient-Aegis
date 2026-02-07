# AEGIS Operator Production Dockerfile
# Multi-stage build for minimal production image

# ===========================================================================
# Stage 0: UV Binary
# ===========================================================================
FROM ghcr.io/astral-sh/uv:0.9.26 AS uv

# ===========================================================================
# Stage 1: Builder
# ===========================================================================
FROM python:3.12-slim-bookworm AS builder

# Set shell with pipefail for safer pipe operations
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy uv binary from official image
COPY --from=uv /uv /usr/local/bin/uv

# Install build dependencies
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files and README (required by hatchling)
COPY pyproject.toml README.md ./
COPY uv.lock* ./

# Create virtual environment and install dependencies using uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN uv venv /app/.venv && \
    uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/

# ===========================================================================
# Stage 2: Runtime
# ===========================================================================
FROM python:3.12-slim-bookworm AS runtime

# Security: Run as non-root user
RUN groupadd --gid 1000 aegis && \
    useradd --uid 1000 --gid aegis --shell /bin/bash --create-home aegis

# Install runtime dependencies only
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set shell with pipefail for safer pipe operations (required before RUN with pipes)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install kubectl and vcluster CLI for shadow management
# PINNING VERSIONS is critical for stability.
# Keep this aligned with the latest stable vCluster release used in demos.
ARG TARGETOS=linux
ARG TARGETARCH=amd64
ARG K8SGPT_VERSION="v0.3.40"
ARG VCLUSTER_VERSION="v0.31.0"

RUN curl -fL -o /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/$(curl -fL -s https://dl.k8s.io/release/stable.txt)/bin/${TARGETOS}/${TARGETARCH}/kubectl" \
    && chmod +x /usr/local/bin/kubectl \
    # Install vCluster (Pinned Version)
    && curl -fL -o /usr/local/bin/vcluster \
      "https://github.com/loft-sh/vcluster/releases/download/${VCLUSTER_VERSION}/vcluster-${TARGETOS}-${TARGETARCH}" \
    && chmod +x /usr/local/bin/vcluster \
    && curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash \
    # Install K8sGPT
    && case "${TARGETARCH}" in \
         "amd64") K8SGPT_ARCH="x86_64" ;; \
         "arm64") K8SGPT_ARCH="arm64" ;; \
         *) K8SGPT_ARCH="${TARGETARCH}" ;; \
       esac \
    && curl -fL -o /tmp/k8sgpt.tar.gz "https://github.com/k8sgpt-ai/k8sgpt/releases/download/${K8SGPT_VERSION}/k8sgpt_Linux_${K8SGPT_ARCH}.tar.gz" \
    && tar -xzf /tmp/k8sgpt.tar.gz -C /tmp \
    && mv /tmp/k8sgpt /usr/local/bin/k8sgpt \
    && chmod +x /usr/local/bin/k8sgpt \
    && rm -f /tmp/k8sgpt.tar.gz

# Set working directory
WORKDIR /app

# Copy virtual environment from builder (includes all dependencies)
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Add venv to PATH
ENV PATH="/app/.venv/bin:${PATH}"

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Switch to non-root user
USER aegis

# Expose metrics port
EXPOSE 8080

# Default command
ENTRYPOINT ["python", "-m", "aegis.k8s_operator.main"]

# Labels
LABEL org.opencontainers.image.source="https://github.com/unifonic/aegis"
LABEL org.opencontainers.image.description="AEGIS - Autonomous SRE Agent with Shadow Verification"
LABEL org.opencontainers.image.licenses="MIT"
