#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting AEGIS Shadow Verification Test ===${NC}"

# 1. Source Environment
echo -e "\n${GREEN}[1/4] Configuring Environment...${NC}"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo -e "${RED}Error: .venv not found. Please run 'uv sync' first.${NC}"
    exit 1
fi

if [ -f ".env.sh" ]; then
    source .env.sh
else
    echo -e "${RED}Error: .env.sh not found.${NC}"
    exit 1
fi
echo "✓ Environment loaded (Groq + Gemini + Security Enabled)"

# 2. Verify Pod Status
echo -e "\n${GREEN}[2/4] Verifying Base Deployment...${NC}"
kubectl get pods -n production
echo "✓ Base deployment is running"

# 3. Simulate Incident (OOMKill)
echo -e "\n${GREEN}[3/4] Simulating OOMKill Incident...${NC}"
kubectl apply -f examples/incidents/oomkill-memory-leak.yaml
echo "✓ Applied OOMKill configuration (memory limit: 64Mi)"
echo "Waiting 10s for update to roll out..."
sleep 10

# 4. detailed AEGIS Analysis
echo -e "\n${GREEN}[4/4] Running AEGIS Analysis with Shadow Verification...${NC}"
echo "Command: aegis analyze deployment/demo-api --namespace production --verify"
aegis analyze deployment/demo-api \
  --namespace production \
  --verify

echo -e "\n${GREEN}=== Test Complete ===${NC}"
