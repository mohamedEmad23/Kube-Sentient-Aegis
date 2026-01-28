# AEGIS Development Container
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Set shell with pipefail for safer pipe operations
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies and uv in single layer
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    jq \
    vim \
    zsh \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /workspaces/unifonic-hackathon

# Copy dependency files first for caching
COPY pyproject.toml uv.lock* ./

# Install Python dependencies
RUN uv sync --frozen --all-extras || uv sync --all-extras

# Install pre-commit hooks
RUN uv run pre-commit install || true

# Set default shell to zsh
ENV SHELL=/bin/zsh

# Labels
LABEL org.opencontainers.image.source="https://github.com/unifonic/aegis"
LABEL org.opencontainers.image.description="AEGIS Development Container"
LABEL org.opencontainers.image.licenses="MIT"
