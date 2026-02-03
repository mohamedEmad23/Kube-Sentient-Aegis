<<<<<<< HEAD
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
=======
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

# Desired tool versions (override via env)
KIND_DESIRED_VERSION="${KIND_VERSION:-v0.24.0}"
KIND_NODE_IMAGE="${KIND_NODE_IMAGE:-kindest/node:v1.30.0}"
KIND_ROOTLESS_ENV=()

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

version_ge() {
    # Returns 0 if $1 >= $2 (semantic-ish compare for vX.Y.Z)
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
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

    # Rootless docker detection (DOCKER_HOST points to /run/user/UID/docker.sock)
    if [[ "${DOCKER_HOST:-}" == *"/run/user/"*"/docker.sock" ]]; then
        log_warn "Detected rootless Docker (DOCKER_HOST=${DOCKER_HOST}). Enabling KIND_EXPERIMENTAL_ROOTLESS=1."
        KIND_ROOTLESS_ENV=("KIND_EXPERIMENTAL_ROOTLESS=1")
        check_rootless_prereqs
    fi
}

check_rootless_prereqs() {
    local uid
    uid="$(id -u)"
    local delegate_conf="/etc/systemd/system/user@.service.d/delegate.conf"
    local user_bus="/run/user/${uid}/bus"
    local subuid_file="/etc/subuid"
    local subgid_file="/etc/subgid"
    local user_name
    user_name="$(id -un)"
    local missing=0

    if [ ! -f "$delegate_conf" ]; then
        log_warn "Missing systemd cgroup delegation for rootless Docker."
        log_warn "Fix:"
        log_warn "  sudo mkdir -p /etc/systemd/system/user@.service.d"
        log_warn "  printf '[Service]\\nDelegate=yes\\n' | sudo tee ${delegate_conf}"
        log_warn "  sudo systemctl daemon-reload"
        log_warn "  sudo systemctl restart user@${uid}.service"
        missing=1
    fi

    if [ ! -S "$user_bus" ]; then
        log_warn "DBus user session socket not found at ${user_bus}."
        log_warn "Fix:"
        log_warn "  sudo apt-get install -y dbus-user-session"
        log_warn "  Then log out and log back in."
        missing=1
    fi

    if ! grep -q "^${user_name}:" "$subuid_file" 2>/dev/null; then
        log_warn "Missing subuid mapping for ${user_name} in ${subuid_file}."
        log_warn "Fix:"
        log_warn "  sudo usermod --add-subuids 100000-165536 ${user_name}"
        missing=1
    fi

    if ! grep -q "^${user_name}:" "$subgid_file" 2>/dev/null; then
        log_warn "Missing subgid mapping for ${user_name} in ${subgid_file}."
        log_warn "Fix:"
        log_warn "  sudo usermod --add-subgids 100000-165536 ${user_name}"
        missing=1
    fi

    if [ -f /proc/sys/user/max_user_namespaces ]; then
        local max_user_ns
        max_user_ns="$(cat /proc/sys/user/max_user_namespaces)"
        if [ "${max_user_ns}" -lt 1 ]; then
            log_warn "user.max_user_namespaces is ${max_user_ns}."
            log_warn "Fix:"
            log_warn "  echo 'user.max_user_namespaces=15000' | sudo tee /etc/sysctl.d/99-rootless.conf"
            log_warn "  sudo sysctl --system"
            missing=1
        fi
    fi

    check_inotify_limits || missing=1

    if [ "$missing" -eq 1 ]; then
        log_error "Rootless prerequisites missing; Kind may fail to boot."
        log_error "Set AEGIS_ROOTLESS_FORCE=1 to continue anyway."
        if [ "${AEGIS_ROOTLESS_FORCE:-0}" != "1" ]; then
            exit 1
        fi
    fi
}

check_inotify_limits() {
    local max_instances max_watches max_queue nofile
    local ok=0

    max_instances="$(cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo 0)"
    max_watches="$(cat /proc/sys/fs/inotify/max_user_watches 2>/dev/null || echo 0)"
    max_queue="$(cat /proc/sys/fs/inotify/max_queued_events 2>/dev/null || echo 0)"
    nofile="$(ulimit -n || echo 0)"

    if [ "$max_instances" -lt 1024 ] || [ "$max_watches" -lt 524288 ] || [ "$max_queue" -lt 16384 ]; then
        log_warn "Inotify limits are low (instances=${max_instances}, watches=${max_watches}, queue=${max_queue})."
        log_warn "Fix:"
        log_warn "  sudo tee /etc/sysctl.d/99-inotify.conf >/dev/null <<'EOF'"
        log_warn "  fs.inotify.max_user_instances=1024"
        log_warn "  fs.inotify.max_user_watches=524288"
        log_warn "  fs.inotify.max_queued_events=16384"
        log_warn "  EOF"
        log_warn "  sudo sysctl --system"
        ok=1
    fi

    if [ "$nofile" -lt 65536 ]; then
        log_warn "Open files limit is low (ulimit -n = ${nofile})."
        log_warn "Fix (systemd user session):"
        log_warn "  sudo mkdir -p /etc/systemd/system/user@.service.d"
        log_warn "  sudo tee /etc/systemd/system/user@.service.d/limits.conf >/dev/null <<'EOF'"
        log_warn "  [Service]"
        log_warn "  DefaultLimitNOFILE=1048576"
        log_warn "  EOF"
        log_warn "  sudo systemctl daemon-reload"
        log_warn "  sudo systemctl restart user@$(id -u).service"
        ok=1
    fi

    return "$ok"
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
        KIND_VERSION_INSTALLED=$(kind version | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
        if [ "$KIND_VERSION_INSTALLED" != "unknown" ] && ! version_ge "$KIND_VERSION_INSTALLED" "$KIND_DESIRED_VERSION"; then
            log_warn "Kind $KIND_VERSION_INSTALLED is older than $KIND_DESIRED_VERSION, upgrading..."
        else
            log_success "Kind $KIND_VERSION_INSTALLED is installed"
            return
        fi
    else
        log_info "Installing Kind..."
    fi
    curl -Lo ./kind "https://kind.sigs.k8s.io/dl/${KIND_DESIRED_VERSION}/kind-${OS_TYPE}-${ARCH}"
    chmod +x ./kind
    sudo mv ./kind /usr/local/bin/kind
    log_success "Kind installed ($KIND_DESIRED_VERSION)"
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
    if ! k8sgpt auth add --backend ollama --baseurl http://localhost:11434 --model phi3:mini; then
        if k8sgpt auth list 2>/dev/null | grep -qi "ollama"; then
            log_warn "K8sGPT Ollama backend already configured; continuing."
        else
            log_error "Failed to configure K8sGPT Ollama backend."
            exit 1
        fi
    fi

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
    local retain_flag=()
    if [ "${AEGIS_KIND_RETAIN:-0}" = "1" ]; then
        retain_flag=(--retain)
        log_warn "AEGIS_KIND_RETAIN=1 set: nodes will be retained on failure."
    fi

    if ! env -u KIND_EXPERIMENTAL_CONTAINERD_SNAPSHOTTER \
        "${KIND_ROOTLESS_ENV[@]}" \
        kind create cluster \
        --config examples/cluster/kind-config.yaml \
        --name aegis-demo \
        --image "${KIND_NODE_IMAGE}" \
        "${retain_flag[@]}"; then
        log_error "Kind cluster creation failed. Exporting logs..."
        kind export logs --name aegis-demo ./kind-logs 2>/dev/null || true
        log_error "Logs (if any) exported to ./kind-logs"
        exit 1
    fi

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
>>>>>>> af4493e9664b4940d61757df392615e5aaeb514e
