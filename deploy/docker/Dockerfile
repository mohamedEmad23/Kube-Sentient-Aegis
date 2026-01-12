# AEGIS Operator Production Dockerfile
# Multi-stage build for minimal production image

# ===========================================================================
# Stage 1: Builder
# ===========================================================================
FROM python:3.12-slim-bookworm AS builder

# Set shell with pipefail for safer pipe operations
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install build dependencies and uv in single layer
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv && uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/

# Build the package
RUN uv build --wheel

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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy built wheel and install
COPY --from=builder /app/dist/*.whl /tmp/
RUN /app/.venv/bin/pip install /tmp/*.whl && rm /tmp/*.whl

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
