#!/bin/bash
# AEGIS K8sGPT Operator Setup Script
#
# This script sets up the K8sGPT operator in a local Kubernetes cluster
# with Ollama as the AI backend.
#
# Prerequisites:
#   - kubectl configured with cluster access
#   - helm v3 installed
#   - Ollama running on host (port 11434)
#
# Usage:
#   ./setup-k8sgpt.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
K8SGPT_NAMESPACE="k8sgpt-system"
OLLAMA_HOST="${OLLAMA_HOST:-host.minikube.internal}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:latest}"

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Please install helm v3."
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Check Ollama connectivity
check_ollama() {
    log_info "Checking Ollama connectivity at ${OLLAMA_HOST}:${OLLAMA_PORT}..."

    # Try to reach Ollama from host
    if curl -s "http://localhost:${OLLAMA_PORT}/api/tags" > /dev/null 2>&1; then
        log_success "Ollama is running on localhost"
    else
        log_warning "Ollama not reachable on localhost:${OLLAMA_PORT}"
        log_info "Make sure Ollama is running: ollama serve"
    fi

    # Check if model is available
    if curl -s "http://localhost:${OLLAMA_PORT}/api/tags" | grep -q "${OLLAMA_MODEL%%:*}"; then
        log_success "Model ${OLLAMA_MODEL} is available"
    else
        log_warning "Model ${OLLAMA_MODEL} not found. Pulling..."
        ollama pull "${OLLAMA_MODEL}" || log_warning "Could not pull model"
    fi
}

# Add K8sGPT Helm repository
add_helm_repo() {
    log_info "Adding K8sGPT Helm repository..."

    helm repo add k8sgpt https://charts.k8sgpt.ai/ || true
    helm repo update

    log_success "Helm repository added"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace ${K8SGPT_NAMESPACE}..."

    kubectl create namespace ${K8SGPT_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

    log_success "Namespace created"
}

# Create K8sGPT secret
create_secret() {
    log_info "Creating K8sGPT secret..."

    kubectl create secret generic k8sgpt-secret \
        --from-literal=apikey=ollama-local-no-auth-required \
        --namespace ${K8SGPT_NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -

    log_success "Secret created"
}

# Install K8sGPT operator
install_operator() {
    log_info "Installing K8sGPT operator..."

    # Get the script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    VALUES_FILE="${SCRIPT_DIR}/../k8sgpt/k8sgpt-values.yaml"

    if [[ -f "${VALUES_FILE}" ]]; then
        helm upgrade --install k8sgpt-operator k8sgpt/k8sgpt-operator \
            --namespace ${K8SGPT_NAMESPACE} \
            --values "${VALUES_FILE}" \
            --wait
    else
        log_warning "Values file not found at ${VALUES_FILE}, using defaults"
        helm upgrade --install k8sgpt-operator k8sgpt/k8sgpt-operator \
            --namespace ${K8SGPT_NAMESPACE} \
            --set k8sgpt.backend=localai \
            --set k8sgpt.model=${OLLAMA_MODEL} \
            --set k8sgpt.baseUrl=http://${OLLAMA_HOST}:${OLLAMA_PORT}/v1 \
            --set k8sgpt.secretName=k8sgpt-secret \
            --wait
    fi

    log_success "K8sGPT operator installed"
}

# Apply K8sGPT CR
apply_k8sgpt_cr() {
    log_info "Applying K8sGPT custom resource..."

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CR_FILE="${SCRIPT_DIR}/../k8sgpt/k8sgpt-cr.yaml"

    if [[ -f "${CR_FILE}" ]]; then
        kubectl apply -f "${CR_FILE}"
    else
        log_info "Creating K8sGPT CR inline..."
        cat <<EOF | kubectl apply -f -
apiVersion: core.k8sgpt.ai/v1alpha1
kind: K8sGPT
metadata:
  name: k8sgpt-aegis
  namespace: ${K8SGPT_NAMESPACE}
spec:
  ai:
    enabled: true
    backend: localai
    model: ${OLLAMA_MODEL}
    baseUrl: http://${OLLAMA_HOST}:${OLLAMA_PORT}/v1
    secret:
      name: k8sgpt-secret
      key: apikey
    anonymize:
      enabled: true
  filters:
    - Pod
    - Deployment
    - ReplicaSet
    - Service
    - StatefulSet
    - PersistentVolumeClaim
    - Node
    - HorizontalPodAutoscaler
  noCache: false
EOF
    fi

    log_success "K8sGPT CR applied"
}

# Wait for operator to be ready
wait_for_operator() {
    log_info "Waiting for K8sGPT operator to be ready..."

    kubectl wait --for=condition=available deployment/k8sgpt-operator \
        --namespace ${K8SGPT_NAMESPACE} \
        --timeout=120s

    log_success "K8sGPT operator is ready"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."

    # Check operator pod
    OPERATOR_POD=$(kubectl get pods -n ${K8SGPT_NAMESPACE} -l app.kubernetes.io/name=k8sgpt-operator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [[ -n "${OPERATOR_POD}" ]]; then
        log_success "Operator pod: ${OPERATOR_POD}"
        kubectl get pods -n ${K8SGPT_NAMESPACE}
    else
        log_warning "Operator pod not found"
    fi

    # Check K8sGPT CR
    if kubectl get k8sgpt -n ${K8SGPT_NAMESPACE} &> /dev/null; then
        log_success "K8sGPT CR exists"
        kubectl get k8sgpt -n ${K8SGPT_NAMESPACE}
    else
        log_warning "K8sGPT CR not found"
    fi

    # Check Result CRD
    if kubectl get crd results.core.k8sgpt.ai &> /dev/null; then
        log_success "Result CRD is installed"
    else
        log_warning "Result CRD not found"
    fi
}

# Deploy test scenario
deploy_test_scenario() {
    log_info "Deploying test scenario (imagepull-bad-tag)..."

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    TEST_FILE="${SCRIPT_DIR}/../../examples/incidents/imagepull-bad-tag.yaml"

    if [[ -f "${TEST_FILE}" ]]; then
        kubectl apply -f "${TEST_FILE}"
        log_success "Test scenario deployed"
        log_info "Wait a few seconds for K8sGPT to detect the issue..."
    else
        log_info "Creating test pod with bad image tag..."
        cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: test-bad-image
  namespace: default
  labels:
    app: test-bad-image
    aegis.io/test: "true"
spec:
  containers:
    - name: test
      image: python:3.99-nonexistent
      command: ["python", "-c", "print('Hello')"]
EOF
        log_success "Test pod created"
    fi
}

# Check for results
check_results() {
    log_info "Checking for K8sGPT Results (wait 30s for analysis)..."

    sleep 30

    RESULTS=$(kubectl get results.core.k8sgpt.ai --all-namespaces -o json 2>/dev/null || echo '{"items":[]}')
    RESULT_COUNT=$(echo "${RESULTS}" | jq '.items | length')

    if [[ "${RESULT_COUNT}" -gt 0 ]]; then
        log_success "Found ${RESULT_COUNT} K8sGPT Result(s)!"
        kubectl get results.core.k8sgpt.ai --all-namespaces
        echo ""
        log_info "View result details:"
        echo "  kubectl get results.core.k8sgpt.ai -A -o yaml"
    else
        log_warning "No Results found yet. K8sGPT may still be analyzing."
        log_info "Check operator logs:"
        echo "  kubectl logs -n ${K8SGPT_NAMESPACE} deployment/k8sgpt-operator"
    fi
}

# Main execution
main() {
    echo ""
    echo "========================================"
    echo "  AEGIS K8sGPT Operator Setup"
    echo "========================================"
    echo ""

    check_prerequisites
    check_ollama
    add_helm_repo
    create_namespace
    create_secret
    install_operator
    wait_for_operator
    apply_k8sgpt_cr
    verify_installation

    echo ""
    log_success "K8sGPT operator setup complete!"
    echo ""
    log_info "Next steps:"
    echo "  1. Deploy a test scenario: kubectl apply -f examples/incidents/imagepull-bad-tag.yaml"
    echo "  2. Wait for K8sGPT to create Results: kubectl get results.core.k8sgpt.ai -A"
    echo "  3. Start AEGIS operator to watch Results: kopf run -m aegis.k8s_operator"
    echo ""

    read -p "Deploy test scenario now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        deploy_test_scenario
        check_results
    fi
}

# Run main function
main "$@"
