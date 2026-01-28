#!/bin/bash
# AEGIS Demo Environment Setup Script
# This script installs all prerequisites for running AEGIS demos
#
# Usage:
#   chmod +x scripts/demo-setup.sh
#   ./scripts/demo-setup.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    arm64) ARCH="arm64" ;;
esac

case "$OS" in
    Linux) OS_TYPE="linux" ;;
    Darwin) OS_TYPE="darwin" ;;
    *) log_error "Unsupported OS: $OS"; exit 1 ;;
esac

log_info "Detected OS: $OS_TYPE, Architecture: $ARCH"

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# ============================================================================
# Docker Check
# ============================================================================
check_docker() {
    log_info "Checking Docker..."
    if command_exists docker; then
        DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        log_success "Docker $DOCKER_VERSION is installed"

        if docker info &> /dev/null; then
            log_success "Docker daemon is running"
        else
            log_error "Docker daemon is not running. Please start Docker."
            exit 1
        fi
    else
        log_error "Docker is not installed. Please install Docker first."
        log_info "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
}

# ============================================================================
# kubectl
# ============================================================================
install_kubectl() {
    log_info "Checking kubectl..."
    if command_exists kubectl; then
        KUBECTL_VERSION=$(kubectl version --client -o json 2>/dev/null | grep -oP '"gitVersion":\s*"v\K[^"]+' || echo "unknown")
        log_success "kubectl $KUBECTL_VERSION is installed"
    else
        log_info "Installing kubectl..."
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/${OS_TYPE}/${ARCH}/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
        log_success "kubectl installed"
    fi
}

# ============================================================================
# Kind (Kubernetes in Docker)
# ============================================================================
install_kind() {
    log_info "Checking Kind..."
    if command_exists kind; then
        KIND_VERSION=$(kind version | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
        log_success "Kind $KIND_VERSION is installed"
    else
        log_info "Installing Kind..."
        curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.20.0/kind-${OS_TYPE}-${ARCH}"
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
        log_success "Kind installed"
    fi
}

# ============================================================================
# Helm
# ============================================================================
install_helm() {
    log_info "Checking Helm..."
    if command_exists helm; then
        HELM_VERSION=$(helm version --short | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
        log_success "Helm $HELM_VERSION is installed"
    else
        log_info "Installing Helm..."
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
        log_success "Helm installed"
    fi
}

# ============================================================================
# K8sGPT
# ============================================================================
install_k8sgpt() {
    log_info "Checking K8sGPT..."
    if command_exists k8sgpt; then
        K8SGPT_VERSION=$(k8sgpt version 2>/dev/null | head -1 || echo "unknown")
        log_success "K8sGPT $K8SGPT_VERSION is installed"
    else
        log_info "Installing K8sGPT..."

        # Get latest version
        K8SGPT_VERSION=$(curl -s https://api.github.com/repos/k8sgpt-ai/k8sgpt/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')

        # Download and install
        case "$OS_TYPE" in
            linux)
                curl -LO "https://github.com/k8sgpt-ai/k8sgpt/releases/download/${K8SGPT_VERSION}/k8sgpt_Linux_${ARCH}.tar.gz"
                tar -xzf "k8sgpt_Linux_${ARCH}.tar.gz"
                sudo mv k8sgpt /usr/local/bin/
                rm -f "k8sgpt_Linux_${ARCH}.tar.gz"
                ;;
            darwin)
                curl -LO "https://github.com/k8sgpt-ai/k8sgpt/releases/download/${K8SGPT_VERSION}/k8sgpt_Darwin_${ARCH}.tar.gz"
                tar -xzf "k8sgpt_Darwin_${ARCH}.tar.gz"
                sudo mv k8sgpt /usr/local/bin/
                rm -f "k8sgpt_Darwin_${ARCH}.tar.gz"
                ;;
        esac
        log_success "K8sGPT installed"
    fi
}

# ============================================================================
# vCluster
# ============================================================================
install_vcluster() {
    log_info "Checking vCluster..."
    if command_exists vcluster; then
        VCLUSTER_VERSION=$(vcluster --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
        log_success "vCluster $VCLUSTER_VERSION is installed"
    else
        log_info "Installing vCluster..."
        curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-${OS_TYPE}-${ARCH}"
        chmod +x vcluster
        sudo mv vcluster /usr/local/bin/
        log_success "vCluster installed"
    fi
}

# ============================================================================
# Ollama
# ============================================================================
install_ollama() {
    log_info "Checking Ollama..."
    if command_exists ollama; then
        OLLAMA_VERSION=$(ollama --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
        log_success "Ollama $OLLAMA_VERSION is installed"
    else
        log_info "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        log_success "Ollama installed"
    fi
}

# ============================================================================
# Configure K8sGPT with Ollama
# ============================================================================
configure_k8sgpt() {
    log_info "Configuring K8sGPT with Ollama backend..."

    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        log_warn "Ollama is not running. Starting Ollama..."
        ollama serve &> /dev/null &
        sleep 3
    fi

    # Pull the model if not present
    log_info "Ensuring phi3:mini model is available..."
    if ! ollama list | grep -q "phi3:mini"; then
        log_info "Pulling phi3:mini model (this may take a few minutes)..."
        ollama pull phi3:mini
    fi

    # Configure K8sGPT
    log_info "Adding Ollama backend to K8sGPT..."
    k8sgpt auth remove --backend ollama 2>/dev/null || true
    k8sgpt auth add --backend ollama --baseurl http://localhost:11434 --model phi3:mini

    log_success "K8sGPT configured with Ollama backend"
}

# ============================================================================
# Create Kind Cluster
# ============================================================================
create_cluster() {
    log_info "Checking for existing aegis-demo cluster..."

    if kind get clusters 2>/dev/null | grep -q "aegis-demo"; then
        log_warn "Cluster 'aegis-demo' already exists"
        read -p "Delete and recreate? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deleting existing cluster..."
            kind delete cluster --name aegis-demo
        else
            log_info "Keeping existing cluster"
            return 0
        fi
    fi

    log_info "Creating Kind cluster 'aegis-demo'..."
    kind create cluster --config examples/cluster/kind-config.yaml --name aegis-demo

    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout=120s

    log_success "Cluster 'aegis-demo' created and ready"
}

# ============================================================================
# Deploy Demo Application
# ============================================================================
deploy_demo_app() {
    log_info "Deploying demo application..."

    # Apply kustomization
    kubectl apply -k examples/demo-app/

    # Wait for deployments
    log_info "Waiting for demo-db to be ready..."
    kubectl wait --for=condition=Ready pod -l app=demo-db -n production --timeout=120s || true

    log_info "Waiting for demo-redis to be ready..."
    kubectl wait --for=condition=Ready pod -l app=demo-redis -n production --timeout=60s || true

    log_info "Waiting for demo-api to be ready..."
    kubectl wait --for=condition=Ready pod -l app=demo-api -n production --timeout=120s || true

    log_success "Demo application deployed"

    # Show status
    log_info "Current pod status:"
    kubectl get pods -n production
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║           AEGIS Demo Environment Setup                           ║"
    echo "║           Autonomous SRE Agent with Shadow Verification          ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    check_docker
    install_kubectl
    install_kind
    install_helm
    install_k8sgpt
    install_vcluster
    install_ollama

    echo ""
    log_success "All prerequisites installed!"
    echo ""

    read -p "Create Kind cluster and deploy demo app? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        create_cluster
        configure_k8sgpt
        deploy_demo_app

        echo ""
        echo "╔══════════════════════════════════════════════════════════════════╗"
        echo "║                    Setup Complete!                               ║"
        echo "╠══════════════════════════════════════════════════════════════════╣"
        echo "║  Demo API available at: http://localhost:30000                   ║"
        echo "║                                                                  ║"
        echo "║  Quick commands:                                                 ║"
        echo "║    kubectl get pods -n production    # View pods                 ║"
        echo "║    k8sgpt analyze --explain          # Run K8sGPT                ║"
        echo "║    aegis analyze pod/demo-api        # Run AEGIS analysis        ║"
        echo "║                                                                  ║"
        echo "║  Inject a failure:                                               ║"
        echo "║    kubectl apply -f examples/incidents/crashloop-missing-env.yaml║"
        echo "╚══════════════════════════════════════════════════════════════════╝"
    else
        log_info "Skipping cluster creation. Run manually with:"
        log_info "  kind create cluster --config examples/cluster/kind-config.yaml --name aegis-demo"
    fi
}

main "$@"
