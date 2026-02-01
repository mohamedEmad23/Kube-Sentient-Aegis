# 🧪 AEGIS Comprehensive Testing Guide

**Last Updated:** 2026-01-27
**Purpose:** End-to-end testing instructions for all AEGIS components

---

## Table of Contents

1. [Quick Start - Run All Tests](#quick-start---run-all-tests)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Docker & Container Tests](#docker--container-tests)
5. [Kubernetes Operator Tests](#kubernetes-operator-tests)
6. [Shadow Manager Tests](#shadow-manager-tests)
7. [Observability Stack Tests](#observability-stack-tests)
8. [Agent Workflow Tests](#agent-workflow-tests)
9. [End-to-End Demo Tests](#end-to-end-demo-tests)
10. [Performance & Load Tests](#performance--load-tests)
11. [Manual Smoke Tests](#manual-smoke-tests)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start - Run All Tests

```bash
# 1. Run all automated tests (15-20 minutes)
make test-all

# 2. Run observability stack validation (5 minutes)
./scripts/test-observability.sh

# 3. Run end-to-end demo (10 minutes)
make test-e2e

# Total: ~35 minutes for complete validation
```

---

## Unit Tests

### 1.1 Test Configuration & Settings

```bash
# Test configuration parsing and validation
uv run pytest tests/unit/test_settings.py -v

# Expected: 10+ tests passing
# Coverage: Pydantic model validation, env parsing, GPU settings
```

**What this tests:**
- ✅ Pydantic BaseSettings validation
- ✅ Environment variable parsing
- ✅ Default value handling
- ✅ GPU configuration detection
- ✅ Invalid configuration rejection

### 1.2 Test Agent State Models

```bash
# Test Pydantic models with new verbose fields
uv run pytest tests/unit/test_state.py -v -k "verbose"

# Expected: Tests for analysis_steps, evidence_summary, decision_rationale
```

**Create if missing:**

```bash
cat > tests/unit/test_state.py << 'EOF'
"""Test agent state models."""
import pytest
from datetime import datetime
from aegis.agent.state import RCAResult, FixProposal, VerificationPlan, IncidentSeverity, LoadTestConfig

def test_rca_result_verbose_fields():
    """Test RCAResult has verbose output fields."""
    rca = RCAResult(
        root_cause="Test cause",
        analysis_steps=["step1", "step2"],
        evidence_summary=["evidence1"],
        decision_rationale="Test rationale",
        severity=IncidentSeverity.HIGH,
        confidence_score=0.9,
        reasoning="Test",
        timestamp=datetime.utcnow()
    )
    assert len(rca.analysis_steps) == 2
    assert len(rca.evidence_summary) == 1
    assert rca.decision_rationale == "Test rationale"

def test_fix_proposal_verbose_fields():
    """Test FixProposal has verbose output fields."""
    fix = FixProposal(
        fix_type="config_change",
        description="Test fix",
        analysis_steps=["step1"],
        decision_rationale="Test rationale",
        commands=["kubectl patch"],
        confidence_score=0.8
    )
    assert len(fix.analysis_steps) == 1
    assert fix.decision_rationale == "Test rationale"

def test_verification_plan_verbose_fields():
    """Test VerificationPlan has verbose output fields."""
    plan = VerificationPlan(
        verification_type="shadow",
        analysis_steps=["step1"],
        decision_rationale="Test rationale",
        test_scenarios=["health"],
        success_criteria=["no errors"],
        duration=60,
        load_test_config=LoadTestConfig(
            users=1, spawn_rate=1, duration_seconds=10, target_url="http://test"
        ),
        security_checks=[]
    )
    assert len(plan.analysis_steps) == 1
    assert plan.decision_rationale == "Test rationale"
    assert plan.security_checks == []

def test_load_test_config_validation():
    """Test LoadTestConfig field validation."""
    with pytest.raises(ValueError):
        LoadTestConfig(users=0, spawn_rate=1, duration_seconds=10, target_url="http://test")

    with pytest.raises(ValueError):
        LoadTestConfig(users=1, spawn_rate=0, duration_seconds=10, target_url="http://test")
EOF

uv run pytest tests/unit/test_state.py -v
```

### 1.3 Test Shadow Manager

```bash
# Test DNS sanitization and namespace building
uv run pytest tests/unit/test_shadow_manager.py -v

# Expected: Tests for _sanitize_name, _build_shadow_namespace
```

**Create if missing:**

```bash
cat > tests/unit/test_shadow_manager.py << 'EOF'
"""Test Shadow Manager functionality."""
import pytest
from aegis.shadow.manager import ShadowManager

def test_sanitize_name():
    """Test DNS-1123 name sanitization."""
    # Test basic sanitization
    assert ShadowManager._sanitize_name("Test_Name") == "test-name"
    assert ShadowManager._sanitize_name("invalid@#name") == "invalid-name"
    assert ShadowManager._sanitize_name("UPPER-lower-123") == "upper-lower-123"

    # Test trailing dash handling
    assert ShadowManager._sanitize_name("test-", allow_trailing_dash=True) == "test-"
    assert ShadowManager._sanitize_name("test-", allow_trailing_dash=False) == "test"

    # Test multiple consecutive dashes
    assert ShadowManager._sanitize_name("test---name") == "test-name"

    # Test empty string fallback
    assert ShadowManager._sanitize_name("@#$%") == "shadow"

def test_build_shadow_namespace():
    """Test shadow namespace construction."""
    manager = ShadowManager()

    # Test normal case
    namespace = manager._build_shadow_namespace("test-123")
    assert namespace.startswith("shadow-")
    assert "test-123" in namespace
    assert len(namespace) <= 63

    # Test truncation for long names
    long_id = "a" * 100
    namespace = manager._build_shadow_namespace(long_id)
    assert len(namespace) <= 63
    assert namespace.startswith("shadow-")

def test_shadow_environment_count():
    """Test active environment counting."""
    manager = ShadowManager()
    assert manager.active_count() == 0
EOF

uv run pytest tests/unit/test_shadow_manager.py -v
```

### 1.4 Test CLI Commands

```bash
# Test CLI argument parsing and display logic
uv run pytest tests/unit/test_cli.py -v

# Expected: 5+ tests passing
# Coverage: Command parsing, result display, error handling
```

### 1.5 Test Metrics & Logging

```bash
# Test Prometheus metrics initialization
uv run pytest tests/unit/test_metrics.py -v

# Test structured logging
uv run pytest tests/unit/test_logging.py -v

# Expected: All metrics defined, logging works correctly
```

### 1.6 Run All Unit Tests

```bash
# Run all unit tests with coverage
make test-unit

# Or with detailed coverage
uv run pytest tests/unit/ -v \
    --cov=aegis \
    --cov-report=term-missing \
    --cov-report=html:htmlcov

# Expected: 25+ tests passing, >75% coverage
```

---

## Integration Tests

### 2.1 Test Agent Workflow

```bash
# Test complete RCA → Solution → Verifier workflow
uv run pytest tests/integration/test_workflow.py -v

# Expected: 13+ tests passing
# What this tests:
# - RCA agent with mock data
# - Solution agent fix generation
# - Verifier agent plan creation
# - Verbose output validation
# - Low confidence routing
# - Error handling
```

**Key Tests:**

```bash
# Test verbose output specifically
uv run pytest tests/integration/test_workflow.py::test_rca_agent_output_structure -v
uv run pytest tests/integration/test_workflow.py::test_solution_agent_output_structure -v
uv run pytest tests/integration/test_workflow.py::test_verifier_agent_output_structure -v

# Expected: All 3 tests pass, verbose fields populated
```

### 2.2 Test Mock Data Fallback

```bash
# Test that mock mode works without cluster
AEGIS_K8S_IN_CLUSTER=false \
AEGIS_MOCK_MODE=true \
uv run pytest tests/integration/test_workflow.py::test_workflow_with_mock_data -v

# Expected: Workflow completes with mock K8sGPT data
```

### 2.3 Run All Integration Tests

```bash
# Run all integration tests
make test-integration

# Expected: 13+ tests passing, 3-5 minutes runtime
```

---

## Docker & Container Tests

### 3.1 Build Docker Image

```bash
# Build the production Docker image
make docker-build

# Expected: Build succeeds, no errors
# Verify: docker images | grep aegis-operator
```

### 3.2 Test Dockerfile Linting

```bash
# Lint Dockerfile with hadolint
hadolint deploy/docker/Dockerfile

# Or use the script
./scripts/hadolint-check.sh

# Expected: No errors, only info messages
```

### 3.3 Test Docker Compose Stack

```bash
# Start observability stack
docker compose -f deploy/docker/docker-compose.yaml up -d

# Wait for services to be ready
sleep 10

# Check all services running
docker compose -f deploy/docker/docker-compose.yaml ps

# Expected: All services in "Up" state
# Services: prometheus, grafana, loki, promtail
```

### 3.4 Test Service Connectivity

```bash
# Test Prometheus
curl -f http://localhost:9090/-/healthy
echo "Prometheus: $?"

# Test Grafana
curl -f http://localhost:3000/api/health
echo "Grafana: $?"

# Test Loki
curl -f http://localhost:3100/ready
echo "Loki: $?"

# Expected: All return 0 (success)
```

### 3.5 Test Alert Rules Loading

```bash
# Check if Prometheus loaded alert rules
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name'

# Expected output:
# "aegis_core_alerts"
# "aegis_shadow_alerts"
# "aegis_operator_alerts"
# "aegis_performance_alerts"
# "aegis_infrastructure_alerts"

# Count total alerts
curl -s http://localhost:9090/api/v1/rules | \
    jq '[.data.groups[].rules[]] | length'

# Expected: 15 (total alert rules)
```

---

## Kubernetes Operator Tests

### 4.1 Setup Test Cluster

```bash
# Create Kind cluster for testing
make demo-cluster-create

# Verify cluster ready
kubectl cluster-info
kubectl get nodes

# Expected: Cluster running, 1 control-plane node ready
```

### 4.2 Install CRDs

```bash
# Install K8sGPT CRDs
kubectl apply -f https://raw.githubusercontent.com/k8sgpt-ai/k8sgpt-operator/main/config/crd/bases/core.k8sgpt.ai_results.yaml

# Verify CRD installed
kubectl get crd results.core.k8sgpt.ai

# Expected: CRD exists
```

### 4.3 Test Operator Deployment

```bash
# Deploy operator to cluster (if you have manifests)
kubectl apply -k deploy/kustomize/base/

# Or run operator locally pointing to cluster
AEGIS_K8S_IN_CLUSTER=false \
uv run python -m aegis.k8s_operator.main &

OPERATOR_PID=$!

# Wait for startup
sleep 5

# Check operator metrics endpoint
curl http://localhost:8080/healthz
curl http://localhost:8080/metrics | grep aegis_system_healthy

# Expected: Healthz returns OK, metrics endpoint works

# Cleanup
kill $OPERATOR_PID
```

### 4.4 Test Handler Logic

```bash
# Create test K8sGPT Result CR
cat <<EOF | kubectl apply -f -
apiVersion: core.k8sgpt.ai/v1alpha1
kind: Result
metadata:
  name: test-result
  namespace: default
spec:
  kind: Pod
  name: test-pod
  error:
    - text: "Pod is in CrashLoopBackOff"
  details: "Container failed to start"
EOF

# Check if operator processes it (watch logs)
kubectl logs -l app=aegis-operator -n aegis-system --tail=50

# Expected: Operator detects CR and processes it
```

---

## Shadow Manager Tests

### 5.1 Test Shadow Namespace Creation

```bash
# Test shadow creation with Python
uv run python << 'EOF'
import asyncio
from aegis.shadow.manager import ShadowManager

async def test_shadow():
    manager = ShadowManager()

    # Test sanitization
    clean_name = manager._sanitize_name("Test@Pod#123")
    print(f"Sanitized: {clean_name}")
    assert clean_name == "test-pod-123"

    # Test namespace building
    namespace = manager._build_shadow_namespace("my-app-20240127")
    print(f"Namespace: {namespace}")
    assert namespace.startswith("shadow-")
    assert len(namespace) <= 63

    print("✅ Shadow manager tests passed")

asyncio.run(test_shadow())
EOF

# Expected: All assertions pass
```

### 5.2 Test Shadow Creation (with cluster)

```bash
# Deploy demo app
make demo-app-deploy

# Wait for app ready
kubectl wait --for=condition=Ready pod -l app=demo-api -n production --timeout=120s

# Test shadow creation
uv run python << 'EOF'
import asyncio
from aegis.shadow.manager import ShadowManager

async def test_create_shadow():
    manager = ShadowManager()

    try:
        env = await manager.create_shadow(
            source_namespace="production",
            source_resource="demo-api",
            source_kind="Deployment"
        )
        print(f"✅ Shadow created: {env.id}")
        print(f"   Namespace: {env.namespace}")
        print(f"   Status: {env.status}")

        # Cleanup
        await manager.cleanup(env.id)
        print("✅ Shadow cleaned up")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise

asyncio.run(test_create_shadow())
EOF

# Expected: Shadow namespace created and cleaned up successfully
```

### 5.3 Verify Shadow Isolation

```bash
# After creating shadow, verify isolation
kubectl get namespaces | grep shadow

# Check pods in shadow namespace
SHADOW_NS=$(kubectl get ns | grep shadow- | head -1 | awk '{print $1}')
kubectl get pods -n "$SHADOW_NS"

# Expected: Shadow namespace exists with cloned resources
```

---

## Observability Stack Tests

### 6.1 Test Metrics Collection

```bash
# Start operator with metrics
AEGIS_K8S_IN_CLUSTER=false \
uv run python -m aegis.k8s_operator.main &

OPERATOR_PID=$!
sleep 5

# Check metrics endpoint
curl http://localhost:8080/metrics | grep -E "aegis_(system_healthy|incidents_detected|agent_iterations)"

# Expected: Multiple AEGIS metrics present

# Test specific metrics
curl -s http://localhost:8080/metrics | grep "aegis_system_healthy"
curl -s http://localhost:8080/metrics | grep "aegis_shadow_environments_active"

# Cleanup
kill $OPERATOR_PID
```

### 6.2 Test Prometheus Scraping

```bash
# Verify Prometheus is scraping operator metrics
curl -s http://localhost:9090/api/v1/targets | \
    jq '.data.activeTargets[] | select(.labels.job=="aegis-operator")'

# Expected: Target present (if operator running)
```

### 6.3 Test Grafana Dashboards

```bash
# Check Grafana datasources
curl -s -u admin:aegis123 http://localhost:3000/api/datasources | \
    jq '.[] | {name, type, url}'

# Expected output:
# {"name":"Prometheus","type":"prometheus","url":"http://prometheus:9090"}
# {"name":"Loki","type":"loki","url":"http://loki:3100"}

# Check dashboards
curl -s -u admin:aegis123 http://localhost:3000/api/search | \
    jq '.[] | {title, uid}'

# Expected: AEGIS dashboard present
```

### 6.4 Test Loki Log Ingestion

```bash
# Send test log to Loki
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H "Content-Type: application/json" \
  -d '{
    "streams": [
      {
        "stream": {"app": "aegis-test"},
        "values": [["'$(date +%s)'000000000", "Test log message"]]
      }
    ]
  }'

# Query logs back
curl -s "http://localhost:3100/loki/api/v1/query_range?query={app=\"aegis-test\"}" | \
    jq '.data.result'

# Expected: Log appears in query results
```

### 6.5 Test Alert Rules Syntax

```bash
# Validate alert rules with promtool
docker run --rm -v "$(pwd)/deploy/docker/prometheus/rules:/rules" \
    prom/prometheus:latest \
    promtool check rules /rules/aegis-alerts.yml

# Expected: No syntax errors, 15 rules validated
```

---

## Agent Workflow Tests

### 7.1 Test CLI Analysis (Mock Mode)

```bash
# Test analysis with mock data (no cluster needed)
uv run aegis analyze pod/demo-nginx --namespace default --mock

# Expected output:
# 1. Root Cause Analysis section with:
#    - Step-by-Step Analysis (3-6 steps)
#    - Evidence Summary (2-5 items)
#    - Decision Rationale
# 2. Fix Proposal section with:
#    - Step-by-Step Analysis
#    - Decision Rationale
#    - Commands
# 3. Verification Plan section with:
#    - Step-by-Step Analysis
#    - Decision Rationale
#    - Test scenarios
```

### 7.2 Test Agent Verbose Output

```bash
# Test that verbose fields are populated
uv run pytest -xvs tests/integration/test_workflow.py::test_rca_agent_output_structure
uv run pytest -xvs tests/integration/test_workflow.py::test_solution_agent_output_structure
uv run pytest -xvs tests/integration/test_workflow.py::test_verifier_agent_output_structure

# Expected: All assertions pass for:
# - analysis_steps (list with 1+ items)
# - evidence_summary (list with 1+ items for RCA)
# - decision_rationale (non-empty string)
```

### 7.3 Test Agent Fallback Logic

```bash
# Test that fallback logic provides defaults when LLM omits fields
uv run python << 'EOF'
import asyncio
from aegis.agent.state import create_initial_state, IncidentSeverity

async def test_agent_fallbacks():
    from aegis.agent.graph import analyze_incident

    result = await analyze_incident(
        resource_type="pod",
        resource_name="test-pod",
        namespace="default",
        mock=True
    )

    rca = result.get("rca_result")
    print(f"RCA analysis_steps: {len(rca.analysis_steps)} items")
    print(f"RCA evidence_summary: {len(rca.evidence_summary)} items")
    print(f"RCA decision_rationale length: {len(rca.decision_rationale)} chars")

    assert len(rca.analysis_steps) >= 1, "Should have analysis steps"
    assert len(rca.evidence_summary) >= 1, "Should have evidence"
    assert len(rca.decision_rationale) > 0, "Should have rationale"

    print("✅ Fallback logic working")

asyncio.run(test_agent_fallbacks())
EOF

# Expected: All assertions pass
```

---

## End-to-End Demo Tests

### 8.1 Full Demo Workflow

```bash
# Complete end-to-end test (15 minutes)

# 1. Start observability stack
docker compose -f deploy/docker/docker-compose.yaml up -d
sleep 10

# 2. Create Kind cluster
make demo-cluster-create

# 3. Deploy demo app
make demo-app-deploy

# 4. Inject incident
make demo-incident-crashloop
sleep 30

# 5. Run AEGIS analysis
uv run aegis analyze pod/nginx-crashloop --namespace production

# 6. Verify analysis output contains:
#    - Root cause identified
#    - Fix proposal generated
#    - Verification plan created
#    - All verbose fields populated

# 7. Check metrics in Prometheus
curl -s http://localhost:9090/api/v1/query?query=aegis_incidents_detected_total | \
    jq '.data.result[0].value'

# 8. View in Grafana
open http://localhost:3000  # Login: admin / aegis123

# 9. Cleanup
make demo-clean
make demo-cluster-delete
docker compose -f deploy/docker/docker-compose.yaml down
```

### 8.2 Test Multiple Incident Types

```bash
# Test all incident scenarios
for incident in crashloop oomkill imagepull liveness; do
    echo "Testing $incident incident..."
    make demo-incident-$incident
    sleep 10
    uv run aegis analyze pod/test-pod --namespace production --mock
    make demo-incident-reset
    sleep 5
done

# Expected: Each incident analyzed successfully
```

---

## Performance & Load Tests

### 9.1 Benchmark Agent Performance

```bash
# Run benchmark tests
uv run pytest tests/benchmarks/ -v --benchmark-only

# Or create a simple benchmark
uv run python << 'EOF'
import asyncio
import time
from aegis.agent.graph import analyze_incident

async def benchmark():
    start = time.time()

    # Run 10 analyses
    for i in range(10):
        result = await analyze_incident(
            resource_type="pod",
            resource_name=f"test-pod-{i}",
            namespace="default",
            mock=True
        )
        assert result["rca_result"] is not None

    elapsed = time.time() - start
    avg = elapsed / 10

    print(f"Total: {elapsed:.2f}s")
    print(f"Average per analysis: {avg:.2f}s")
    print(f"Throughput: {10/elapsed:.2f} analyses/sec")

    assert avg < 5.0, "Average should be under 5 seconds"
    print("✅ Performance acceptable")

asyncio.run(benchmark())
EOF

# Expected: <5 seconds per analysis in mock mode
```

### 9.2 Test Concurrent Analysis

```bash
# Test multiple concurrent analyses
uv run python << 'EOF'
import asyncio
from aegis.agent.graph import analyze_incident

async def concurrent_test():
    tasks = [
        analyze_incident(f"pod", f"test-{i}", "default", mock=True)
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)

    print(f"Completed {len(results)} concurrent analyses")
    assert all(r["rca_result"] is not None for r in results)
    print("✅ Concurrent analysis working")

asyncio.run(concurrent_test())
EOF

# Expected: All 5 analyses complete successfully
```

---

## Manual Smoke Tests

### 10.1 Visual Verification Checklist

```bash
# Start full stack
docker compose -f deploy/docker/docker-compose.yaml up -d
sleep 10

# ✅ Check 1: Prometheus UI
open http://localhost:9090
# Verify:
# - [ ] UI loads
# - [ ] Status → Targets shows services
# - [ ] Status → Rules shows 15 aegis alerts
# - [ ] No alerts firing (if clean system)

# ✅ Check 2: Grafana UI
open http://localhost:3000  # admin / aegis123
# Verify:
# - [ ] Login works
# - [ ] Dashboards → AEGIS Overview exists
# - [ ] Dashboard panels load (may be empty without data)
# - [ ] No datasource errors

# ✅ Check 3: CLI Help
uv run aegis --help
# Verify:
# - [ ] Shows all commands
# - [ ] No import errors
# - [ ] Version displayed

# ✅ Check 4: CLI Analysis
uv run aegis analyze pod/test --namespace default --mock
# Verify:
# - [ ] Analysis completes
# - [ ] Shows 3 sections (RCA, Fix, Verification)
# - [ ] Verbose output present (analysis steps, evidence, rationale)
# - [ ] No Python errors

# ✅ Check 5: Mock Mode
uv run aegis analyze pod/nginx --namespace default --mock
# Verify:
# - [ ] Uses mock K8sGPT data
# - [ ] Generates realistic incident
# - [ ] Complete workflow finishes
```

---

## Troubleshooting

### Common Issues

**1. Tests fail with "Cannot connect to Docker daemon"**
```bash
# Start Docker service
sudo systemctl start docker

# Or on macOS
open -a Docker
```

**2. Pytest import errors**
```bash
# Reinstall with dev dependencies
uv sync --frozen --all-extras

# Verify PYTHONPATH
export PYTHONPATH=/home/mohammed-emad/VS-CODE/unifonic-hackathon/src:$PYTHONPATH
```

**3. Kubernetes cluster not accessible**
```bash
# Check cluster status
kubectl cluster-info

# Reset context
kubectl config use-context kind-aegis-demo
```

**4. Prometheus not scraping**
```bash
# Check Prometheus logs
docker logs aegis-prometheus

# Verify alert rules loaded
curl http://localhost:9090/api/v1/rules | jq
```

**5. Grafana datasource errors**
```bash
# Restart Grafana
docker compose -f deploy/docker/docker-compose.yaml restart grafana

# Check datasource config
cat deploy/docker/grafana/provisioning/datasources/datasources.yaml
```

**6. Agent tests timeout**
```bash
# Increase timeout in pytest
uv run pytest tests/integration/ -v --timeout=120

# Or skip slow tests
uv run pytest tests/integration/ -v -m "not slow"
```

---

## Test Coverage Report

```bash
# Generate HTML coverage report
make test-cov

# View report
open htmlcov/index.html

# Expected coverage:
# - Overall: >75%
# - Core modules: >80%
# - Agent code: >85%
```

---

## Summary Test Script

```bash
#!/bin/bash
# Complete test suite runner

echo "🧪 AEGIS Complete Test Suite"
echo "=============================="

# 1. Unit tests
echo "Running unit tests..."
make test-unit || exit 1

# 2. Integration tests
echo "Running integration tests..."
make test-integration || exit 1

# 3. Docker build
echo "Building Docker image..."
make docker-build || exit 1

# 4. Docker compose stack
echo "Starting observability stack..."
docker compose -f deploy/docker/docker-compose.yaml up -d
sleep 15

# 5. Verify services
echo "Checking services..."
curl -sf http://localhost:9090/-/healthy || exit 1
curl -sf http://localhost:3000/api/health || exit 1
curl -sf http://localhost:3100/ready || exit 1

# 6. Verify alert rules
echo "Checking alert rules..."
ALERT_COUNT=$(curl -s http://localhost:9090/api/v1/rules | jq '[.data.groups[].rules[]] | length')
if [ "$ALERT_COUNT" -ne 15 ]; then
    echo "❌ Expected 15 alert rules, found $ALERT_COUNT"
    exit 1
fi

# 7. CLI smoke test
echo "Testing CLI..."
uv run aegis analyze pod/test --namespace default --mock > /tmp/aegis_output.txt
grep -q "Step-by-Step Analysis" /tmp/aegis_output.txt || exit 1
grep -q "Evidence Summary" /tmp/aegis_output.txt || exit 1
grep -q "Decision Rationale" /tmp/aegis_output.txt || exit 1

# Cleanup
docker compose -f deploy/docker/docker-compose.yaml down

echo ""
echo "✅ All tests passed!"
echo "=============================="
echo "Test Summary:"
echo "  - Unit tests: PASS"
echo "  - Integration tests: PASS"
echo "  - Docker build: PASS"
echo "  - Observability stack: PASS"
echo "  - Alert rules: 15/15 loaded"
echo "  - CLI verbose output: PASS"
echo ""
echo "🏆 System ready for hackathon submission!"
```

Save this script as `scripts/test-all.sh` and run:

```bash
chmod +x scripts/test-all.sh
./scripts/test-all.sh
```

---

**Total Testing Time:**
- Unit tests: 2 minutes
- Integration tests: 5 minutes
- Docker/Observability: 10 minutes
- Manual verification: 5 minutes
- **Total: ~22 minutes for comprehensive validation**
