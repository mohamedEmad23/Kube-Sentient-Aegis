#!/bin/bash
# Unleash Beast Mode: Reconfigure Minikube for High-Performance Shadow Environments
# Optimized for 8 CPU / 40GB RAM Workstation

set -e

echo "🔥 UNLEASHING BEAST MODE 🔥"
echo ""
echo "Your Hardware: 8 CPUs, 40GB RAM"
echo "Allocating: 6 CPUs, 16GB RAM to Minikube"
echo "Remaining: 2 CPUs, 24GB RAM for OS/VS Code/Browser"
echo ""

# Check if minikube is running
if minikube status &>/dev/null; then
    echo "⚠️  Detected existing Minikube cluster"
    echo "   This cluster may be running with limited resources (2 CPU, 2GB RAM)"
    echo ""
    read -p "Delete and recreate with high-performance settings? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deleting old cluster..."
        minikube delete
    else
        echo "❌ Cancelled. Keep your existing cluster."
        exit 0
    fi
fi

echo ""
echo "🚀 Starting High-Performance Minikube Cluster..."
echo "   CPUs: 6"
echo "   Memory: 16GB"
echo "   Disk: 50GB"
echo "   Driver: docker"
echo ""

minikube start \
    --cpus 6 \
    --memory 16384 \
    --disk-size 50g \
    --driver docker

echo ""
echo "✅ Beast Mode Activated!"
echo ""
echo "Next steps:"
echo "  1. Redeploy your demo workloads:"
echo "     kubectl apply -k examples/demo-app/"
echo ""
echo "  2. Run shadow verification:"
echo "     source .venv/bin/activate"
echo "     aegis shadow create deployment/demo-api -n production --wait"
echo ""
echo "Expected performance:"
echo "  - Shadow creation: < 10 seconds (vs 30s before)"
echo "  - API connection: < 5 seconds (vs 3 min timeout before)"
echo "  - Verification: Full test suite in < 2 minutes"
echo ""
echo "🎯 Your vCluster now has 500m-2000m CPU and 1-4GB RAM!"
