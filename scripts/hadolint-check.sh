#!/bin/bash
# =============================================================================
# AEGIS Hadolint Dual-Mode Linting Script
# =============================================================================
#
# PURPOSE:
#   Production-grade Dockerfile linting supporting both local and CI/CD
#   environments. This script ensures consistent linting behavior across
#   all development and deployment contexts.
#
# EXECUTION MODES:
#   1. Local Binary Mode  - Uses system-installed hadolint (fastest)
#   2. Docker Mode        - Falls back to hadolint Docker image
#   3. Explicit Failure   - Fails with clear instructions if neither available
#
# USAGE:
#   ./scripts/hadolint-check.sh [Dockerfile paths...]
#   ./scripts/hadolint-check.sh deploy/docker/Dockerfile
#
# INSTALLATION:
#   macOS:   brew install hadolint
#   Linux:   wget -O /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 && chmod +x /usr/local/bin/hadolint
#   Docker:  Automatically used as fallback
#
# EXIT CODES:
#   0 - All Dockerfiles passed linting
#   1 - Linting errors found
#   2 - No linting tool available (hadolint not installed, Docker not running)
#
# =============================================================================

set -euo pipefail

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Hadolint Docker image (official)
HADOLINT_IMAGE="hadolint/hadolint:latest-alpine"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[HADOLINT]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[HADOLINT]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[HADOLINT]${NC} $1"
}

log_error() {
    echo -e "${RED}[HADOLINT]${NC} $1" >&2
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if Docker is available and running
docker_available() {
    command_exists docker && docker info &> /dev/null
}

# -----------------------------------------------------------------------------
# Linting Functions
# -----------------------------------------------------------------------------

# Lint using local hadolint binary
lint_with_local() {
    local files=("$@")
    log_info "Using local hadolint binary: $(command -v hadolint)"

    local exit_code=0
    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            log_info "Linting: $file"
            if ! hadolint "$file"; then
                exit_code=1
            fi
        else
            log_warn "File not found: $file"
        fi
    done

    return $exit_code
}

# Lint using Docker container
lint_with_docker() {
    local files=("$@")
    log_info "Using Docker image: $HADOLINT_IMAGE"

    # Pull image if not present (silent in CI)
    if ! docker image inspect "$HADOLINT_IMAGE" &> /dev/null; then
        log_info "Pulling hadolint Docker image..."
        docker pull "$HADOLINT_IMAGE" > /dev/null
    fi

    local exit_code=0
    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            log_info "Linting: $file"
            # Mount file and run hadolint
            if ! docker run --rm -i "$HADOLINT_IMAGE" < "$file"; then
                exit_code=1
            fi
        else
            log_warn "File not found: $file"
        fi
    done

    return $exit_code
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------

main() {
    # Collect Dockerfile paths from arguments
    local files=("$@")

    # If no files provided, exit successfully (no Dockerfiles to lint)
    if [[ ${#files[@]} -eq 0 ]]; then
        log_info "No Dockerfiles provided for linting"
        exit 0
    fi

    log_info "Starting Dockerfile linting (${#files[@]} file(s))"

    # Mode 1: Try local hadolint binary first (fastest)
    if command_exists hadolint; then
        if lint_with_local "${files[@]}"; then
            log_success "All Dockerfiles passed linting (local mode)"
            exit 0
        else
            log_error "Dockerfile linting failed"
            exit 1
        fi
    fi

    # Mode 2: Fall back to Docker if available
    if docker_available; then
        log_warn "Local hadolint not found, using Docker fallback"
        if lint_with_docker "${files[@]}"; then
            log_success "All Dockerfiles passed linting (Docker mode)"
            exit 0
        else
            log_error "Dockerfile linting failed"
            exit 1
        fi
    fi

    # Mode 3: Neither available - explicit failure with instructions
    log_error "============================================================"
    log_error "HADOLINT NOT AVAILABLE"
    log_error "============================================================"
    log_error ""
    log_error "Neither local hadolint binary nor Docker is available."
    log_error "Please install hadolint using one of these methods:"
    log_error ""
    log_error "  macOS (Homebrew):"
    log_error "    brew install hadolint"
    log_error ""
    log_error "  Linux (binary):"
    log_error "    wget -O /usr/local/bin/hadolint \\"
    log_error "      https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64"
    log_error "    chmod +x /usr/local/bin/hadolint"
    log_error ""
    log_error "  Any OS (Docker):"
    log_error "    Ensure Docker is installed and running"
    log_error ""
    log_error "For CI/CD, add hadolint to your workflow or use Docker-in-Docker."
    log_error "============================================================"
    exit 2
}

main "$@"
