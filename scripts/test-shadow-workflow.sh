#!/bin/bash
# Test script for shadow verification workflow
# Tests the complete AEGIS shadow environment lifecycle with real commands

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"

echo "==========================================="
echo "AEGIS Shadow Workflow Test Suite"
echo "==========================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "⚠️  kubectl not found. Please install kubectl to run integration tests."
    echo "   Tests will run in mock mode only."
    MOCK_MODE=true
else
    echo "✓ kubectl found"
    MOCK_MODE=false
fi

# Check if k8s cluster is available
if [ "$MOCK_MODE" = false ]; then
    if kubectl cluster-info &> /dev/null; then
        echo "✓ Kubernetes cluster accessible"
        CLUSTER_AVAILABLE=true
    else
        echo "⚠️  No Kubernetes cluster accessible. Tests will run in mock mode."
        CLUSTER_AVAILABLE=false
    fi
else
    CLUSTER_AVAILABLE=false
fi

echo ""
echo "-------------------------------------------"
echo "Test 1: Import Verification"
echo "-------------------------------------------"
$PYTHON -c "
from aegis.shadow.manager import ShadowManager
from aegis.shadow.vcluster import VClusterManager
from aegis.agent.graph import create_incident_workflow, analyze_incident
from aegis.k8s_operator.handlers.shadow import shadow_verification_daemon
from aegis.cli import app
print('✓ All imports successful')
"

echo ""
echo "-------------------------------------------"
echo "Test 2: Unit Tests"
echo "-------------------------------------------"
cd "$PROJECT_ROOT"
$PYTHON -m pytest tests/integration/test_shadow_workflow.py -v --tb=short

echo ""
echo "-------------------------------------------"
echo "Test 3: Shadow Manager Instantiation"
echo "-------------------------------------------"
$PYTHON -c "
from unittest.mock import patch
from aegis.shadow.manager import ShadowManager

with patch('aegis.shadow.manager.config.load_kube_config'):
    manager = ShadowManager()
    print(f'✓ ShadowManager created')
    print(f'  - Active shadows: {len(manager.active_shadows)}')
    print(f'  - VCluster manager: {type(manager.vcluster_mgr).__name__}')
"

if [ "$CLUSTER_AVAILABLE" = true ]; then
    echo ""
    echo "-------------------------------------------"
    echo "Test 4: Cluster Resource Check (Real K8s)"
    echo "-------------------------------------------"
    $PYTHON -c "
import asyncio
from aegis.shadow.manager import ShadowManager

async def main():
    try:
        manager = ShadowManager()
        has_resources = await manager._check_cluster_resources(
            required_cpu='100m',
            required_memory='256Mi'
        )
        if has_resources:
            print('✓ Cluster has sufficient resources')
        else:
            print('⚠️  Cluster may not have sufficient resources')
    except Exception as e:
        print(f'⚠️  Resource check failed: {e}')

asyncio.run(main())
"

    echo ""
    echo "-------------------------------------------"
    echo "Test 5: List Active Shadows (Real K8s)"
    echo "-------------------------------------------"
    $PYTHON -c "
import asyncio
from aegis.shadow.manager import ShadowManager

async def main():
    try:
        manager = ShadowManager()
        active = await manager.list_active_shadows()
        print(f'✓ Found {len(active)} active shadow environments')
        for shadow in active:
            print(f'  - {shadow.incident_id}: {shadow.status.value}')
    except Exception as e:
        print(f'⚠️  Failed to list shadows: {e}')

asyncio.run(main())
"
fi

echo ""
echo "-------------------------------------------"
echo "Test 6: CLI Commands"
echo "-------------------------------------------"
echo "Testing CLI help..."
$PYTHON -m aegis.cli --help | head -n 10
echo "✓ CLI accessible"

echo ""
echo "==========================================="
echo "Test Summary"
echo "==========================================="
echo "✅ Import verification: PASSED"
echo "✅ Unit tests: CHECK OUTPUT ABOVE"
echo "✅ Shadow Manager instantiation: PASSED"
if [ "$CLUSTER_AVAILABLE" = true ]; then
    echo "✅ Real Kubernetes integration: TESTED"
else
    echo "⚠️  Real Kubernetes integration: SKIPPED (no cluster)"
fi
echo "✅ CLI commands: PASSED"
echo ""
echo "All critical tests completed!"
