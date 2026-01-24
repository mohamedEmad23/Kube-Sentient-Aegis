#!/bin/bash
# AEGIS Minikube Setup Script
#
# This script sets up a local minikube cluster for AEGIS development
# with all required addons and configurations.
#
# Usage:
#   ./setup-minikube.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
PROFILE="${MINIKUBE_PROFILE:-aegis}"
CPUS="${MINIKUBE_CPUS:-4}"
MEMORY="${MINIKUBE_MEMORY:-8192}"
DRIVER="${MINIKUBE_DRIVER:-docker}"
K8S_VERSION="${MINIKUBE_K8S_VERSION:-v1.29.0}"

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v minikube &> /dev/null; then
        log_error "minikube not found. Install from: https://minikube.sigs.k8s.io/"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Install kubectl first."
        exit 1
    fi

    if ! command -v docker &> /dev/null && [[ "${DRIVER}" == "docker" ]]; then
        log_error "docker not found. Install docker or use a different driver."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Start minikube
start_minikube() {
    log_info "Starting minikube cluster: ${PROFILE}..."

    # Check if cluster already exists
    if minikube status -p "${PROFILE}" &> /dev/null; then
        log_warning "Cluster ${PROFILE} already exists"
        read -p "Delete and recreate? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            minikube delete -p "${PROFILE}"
        else
            log_info "Starting existing cluster..."
            minikube start -p "${PROFILE}"
            return
        fi
    fi

    # Start new cluster
    minikube start \
        --profile="${PROFILE}" \
        --cpus="${CPUS}" \
        --memory="${MEMORY}" \
        --driver="${DRIVER}" \
        --kubernetes-version="${K8S_VERSION}" \
        --extra-config=apiserver.enable-admission-plugins=NamespaceLifecycle,LimitRanger,ServiceAccount,DefaultStorageClass,DefaultTolerationSeconds,NodeRestriction,MutatingAdmissionWebhook,ValidatingAdmissionWebhook,ResourceQuota

    log_success "Minikube cluster started"
}

# Enable addons
enable_addons() {
    log_info "Enabling addons..."

    minikube addons enable metrics-server -p "${PROFILE}"
    minikube addons enable ingress -p "${PROFILE}"
    minikube addons enable ingress-dns -p "${PROFILE}"

    log_success "Addons enabled"
}

# Configure kubectl context
configure_kubectl() {
    log_info "Configuring kubectl context..."

    kubectl config use-context "${PROFILE}"

    # Verify connectivity
    if kubectl cluster-info &> /dev/null; then
        log_success "kubectl configured and connected"
    else
        log_error "Failed to connect to cluster"
        exit 1
    fi
}

# Create namespaces
create_namespaces() {
    log_info "Creating namespaces..."

    kubectl create namespace aegis-system --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace k8sgpt-system --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace aegis-test --dry-run=client -o yaml | kubectl apply -f -

    log_success "Namespaces created"
}

# Show cluster info
show_info() {
    echo ""
    echo "========================================"
    echo "  AEGIS Minikube Cluster Ready"
    echo "========================================"
    echo ""

    log_info "Cluster: ${PROFILE}"
    log_info "Kubernetes: ${K8S_VERSION}"
    log_info "CPUs: ${CPUS}"
    log_info "Memory: ${MEMORY}MB"
    log_info "Driver: ${DRIVER}"

    echo ""
    log_info "Namespaces:"
    kubectl get namespaces | grep -E 'aegis|k8sgpt'

    echo ""
    log_info "Nodes:"
    kubectl get nodes

    echo ""
    log_info "Ollama access from cluster:"
    echo "  URL: http://host.minikube.internal:11434"
    echo ""

    log_info "Next steps:"
    echo "  1. Ensure Ollama is running: ollama serve"
    echo "  2. Install K8sGPT: ./setup-k8sgpt.sh"
    echo "  3. Run AEGIS operator: kopf run -m aegis.k8s_operator"
    echo ""

    log_info "Useful commands:"
    echo "  minikube dashboard -p ${PROFILE}    # Open dashboard"
    echo "  minikube ssh -p ${PROFILE}          # SSH into node"
    echo "  minikube stop -p ${PROFILE}         # Stop cluster"
    echo "  minikube delete -p ${PROFILE}       # Delete cluster"
    echo ""
}

# Main
main() {
    echo ""
    echo "========================================"
    echo "  AEGIS Minikube Setup"
    echo "========================================"
    echo ""

    check_prerequisites
    start_minikube
    enable_addons
    configure_kubectl
    create_namespaces
    show_info
}

main "$@"
