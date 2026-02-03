#!/bin/bash
# Quick Start: Test AEGIS Shadow Layer with Real Kubernetes

set -e

echo "=================================================="
echo "AEGIS Shadow Layer - Quick Start Test"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CD="/home/mohammed-emad/VS-CODE/unifonic-hackathon"
PYTHON="$CD/.venv/bin/python"
AEGIS="$PYTHON -m aegis.cli"

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}✗ Kubectl not connected to cluster${NC}"
    echo "Run: minikube start --cpus=4 --memory=8192"
    exit 1
fi
echo -e "${GREEN}✓ Kubernetes cluster accessible${NC}"

if ! command -v vcluster &> /dev/null; then
    echo -e "${YELLOW}⚠ vCluster CLI not found. Installing...${NC}"
    curl -L -o /tmp/vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
    chmod +x /tmp/vcluster
    sudo mv /tmp/vcluster /usr/local/bin/
fi
echo -e "${GREEN}✓ vCluster CLI installed${NC}"

if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo -e "${RED}✗ Ollama not running${NC}"
    echo "Start Ollama in another terminal: ollama serve"
    exit 1
fi
echo -e "${GREEN}✓ Ollama running${NC}"

echo ""

# Step 2: Deploy test application
echo -e "${YELLOW}Step 2: Deploying test application...${NC}"

kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: aegis-test
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-nginx
  namespace: aegis-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-nginx
  template:
    metadata:
      labels:
        app: test-nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 100m
            memory: 128Mi
EOF

echo -e "${GREEN}✓ Test application deployed${NC}"

# Wait for deployment
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=60s deployment/test-nginx -n aegis-test
echo -e "${GREEN}✓ Deployment ready${NC}"
echo ""

# Step 3: Test resource availability check
echo -e "${YELLOW}Step 3: Testing resource availability check...${NC}"

$PYTHON -c "
import asyncio
from aegis.shadow.manager import ShadowManager

async def main():
    manager = ShadowManager()
    result = await manager._check_cluster_resources(
        required_cpu='500m',
        required_memory='1Gi'
    )

    print(f'  Sufficient: {result[\"sufficient\"]}')
    print(f'  Available CPU: {result[\"available_cpu\"]}')
    print(f'  Available Memory: {result[\"available_memory\"]}')

    if not result['sufficient']:
        print('  ⚠️ WARNING: May have insufficient resources')
    return result['sufficient']

if asyncio.run(main()):
    exit(0)
else:
    exit(1)
" && echo -e "${GREEN}✓ Resource check passed${NC}" || echo -e "${YELLOW}⚠ Resource check warning${NC}"

echo ""

# Step 4: Create shadow environment
echo -e "${YELLOW}Step 4: Creating shadow environment...${NC}"
echo "This will take 1-3 minutes..."

SHADOW_ID="test-$(date +%s)"

$AEGIS shadow create deployment/test-nginx -n aegis-test --id $SHADOW_ID --wait && \
echo -e "${GREEN}✓ Shadow environment created: $SHADOW_ID${NC}" || \
echo -e "${RED}✗ Shadow creation failed${NC}"

echo ""

# Step 5: List shadows
echo -e "${YELLOW}Step 5: Listing shadow environments...${NC}"
$AEGIS shadow list

echo ""

# Step 6: Check shadow status
echo -e "${YELLOW}Step 6: Checking shadow status...${NC}"
$AEGIS shadow status $SHADOW_ID

echo ""

# Step 7: Cleanup
echo -e "${YELLOW}Step 7: Cleaning up...${NC}"
$AEGIS shadow delete $SHADOW_ID 2>/dev/null || echo "Shadow already cleaned up"
kubectl delete namespace aegis-test --wait=false

echo ""
echo -e "${GREEN}=================================================="
echo "Quick Start Test Complete!"
echo -e "==================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Test analysis: aegis analyze deployment/test-nginx -n aegis-test"
echo "  2. Test with verification: aegis analyze deployment/test-nginx -n aegis-test --verify"
echo "  3. See REAL_WORLD_TESTING.md for more scenarios"
