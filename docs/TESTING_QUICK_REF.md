# 🧪 AEGIS Testing Quick Reference

**Last Updated:** 2026-01-27

## Quick Commands

```bash
# Run everything (20-25 minutes)
make test-all

# Unit tests only (2 minutes)
make test-unit

# Integration tests only (5 minutes)
make test-integration

# With coverage report
make test-cov
```

## Component-Specific Tests

### 1. Test CLI

```bash
# Test with mock data
uv run aegis analyze pod/test --namespace default --mock

# Verify verbose output present
uv run aegis analyze pod/test --namespace default --mock | \
    grep -E "Step-by-Step Analysis|Evidence Summary|Decision Rationale"
```

### 2. Test Docker Stack

```bash
# Start stack
docker compose -f deploy/docker/docker-compose.yaml up -d

# Check services
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health # Grafana
curl http://localhost:3100/ready      # Loki

# Stop stack
docker compose -f deploy/docker/docker-compose.yaml down
```

### 3. Test Alert Rules

```bash
# Start Prometheus
docker compose -f deploy/docker/docker-compose.yaml up -d prometheus

# Check alert rules loaded
curl -s http://localhost:9090/api/v1/rules | \
    jq '.data.groups[].name'

# Expected: 5 groups
# - aegis_core_alerts
# - aegis_shadow_alerts
# - aegis_operator_alerts
# - aegis_performance_alerts
# - aegis_infrastructure_alerts

# Count total alerts
curl -s http://localhost:9090/api/v1/rules | \
    jq '[.data.groups[].rules[]] | length'

# Expected: 15
```

### 4. Test Agent Verbose Output

```bash
# Test RCA output structure
uv run pytest tests/integration/test_workflow.py::test_rca_agent_output_structure -v

# Test Solution output structure
uv run pytest tests/integration/test_workflow.py::test_solution_agent_output_structure -v

# Test Verifier output structure
uv run pytest tests/integration/test_workflow.py::test_verifier_agent_output_structure -v

# All 3 tests should pass with verbose fields populated
```

### 5. Test Shadow Manager

```bash
# Test DNS sanitization
uv run python << 'EOF'
from aegis.shadow.manager import ShadowManager

# Test sanitization examples
examples = [
    ("Test_Name", "test-name"),
    ("UPPER-lower-123", "upper-lower-123"),
    ("invalid@#name", "invalid-name"),
    ("test---name", "test-name"),
]

for input_val, expected in examples:
    result = ShadowManager._sanitize_name(input_val)
    assert result == expected, f"{input_val} -> {result} (expected {expected})"
    print(f"✅ {input_val} -> {result}")

print("\n✅ All sanitization tests passed!")
EOF
```

### 6. Test Grafana

```bash
# Check datasources
curl -s -u admin:aegis123 http://localhost:3000/api/datasources | \
    jq '.[] | {name, type, url}'

# Expected:
# Prometheus: http://prometheus:9090
# Loki: http://loki:3100

# Check dashboards
curl -s -u admin:aegis123 http://localhost:3000/api/search | \
    jq '.[] | {title, uid}'

# Expected: "AEGIS - Autonomous SRE Overview"
```

### 7. Test with Kubernetes Cluster

```bash
# Create Kind cluster
make demo-cluster-create

# Deploy demo app
make demo-app-deploy

# Inject incident
make demo-incident-crashloop

# Wait for pod to fail
kubectl wait --for=condition=Ready=false pod -l app=nginx-crashloop \
    -n production --timeout=60s || true

# Analyze with AEGIS
uv run aegis analyze pod/nginx-crashloop --namespace production

# Cleanup
make demo-clean
make demo-cluster-delete
```

## Verification Checklist

After running tests, verify:

- [ ] All unit tests pass (20+ tests)
- [ ] All integration tests pass (13+ tests)
- [ ] Docker image builds successfully
- [ ] Prometheus loads 15 alert rules
- [ ] Grafana has 2 datasources (Prometheus + Loki)
- [ ] CLI analysis shows verbose output:
  - [ ] Step-by-Step Analysis
  - [ ] Evidence Summary
  - [ ] Decision Rationale
- [ ] No Python import errors
- [ ] No container crashes

## Expected Test Results

```
Component                  Status    Tests    Time
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unit Tests                 ✅        25+      2 min
Integration Tests          ✅        13+      5 min
Docker Build               ✅         1       2 min
Observability Stack        ✅         4       3 min
Alert Rules                ✅        15       1 min
CLI Verbose Output         ✅         3       1 min
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total                      ✅        61+     ~14 min
```

## Troubleshooting

### Tests fail with import errors

```bash
# Reinstall dependencies
uv sync --frozen --all-extras

# Set PYTHONPATH
export PYTHONPATH=/home/mohammed-emad/VS-CODE/unifonic-hackathon/src:$PYTHONPATH
```

### Docker services not starting

```bash
# Check Docker daemon
docker ps

# Restart Docker (Linux)
sudo systemctl restart docker

# View logs
docker compose -f deploy/docker/docker-compose.yaml logs
```

### Alert rules not loading

```bash
# Check Prometheus logs
docker logs aegis-prometheus

# Validate rules syntax
docker run --rm -v "$(pwd)/deploy/docker/prometheus/rules:/rules" \
    prom/prometheus:latest \
    promtool check rules /rules/aegis-alerts.yml
```

### Grafana datasources not working

```bash
# Restart Grafana
docker compose -f deploy/docker/docker-compose.yaml restart grafana

# Check datasource config
cat deploy/docker/grafana/provisioning/datasources/datasources.yaml
```

## Pre-Demo Checklist

Before hackathon demo:

```bash
# 1. Run full test suite
make test-all

# 2. Start observability stack
docker compose -f deploy/docker/docker-compose.yaml up -d

# 3. Verify all services healthy
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
curl http://localhost:3100/ready

# 4. Test CLI
uv run aegis analyze pod/demo --namespace default --mock

# 5. Open Grafana
open http://localhost:3000  # admin / aegis123

# 6. Open Prometheus
open http://localhost:9090

# You're ready! 🚀
```

## Coverage Threshold

Minimum coverage requirements:
- Overall: **≥75%**
- Core modules: **≥80%**
- Agent code: **≥85%**

Check coverage:
```bash
make test-cov
open htmlcov/index.html
```

## CI/CD Integration

Add to GitHub Actions / GitLab CI:

```yaml
test:
  script:
    - uv sync --frozen --all-extras
    - make test-unit
    - make test-integration
    - make docker-build
```

---

**For complete testing guide, see:** [TESTING_GUIDE.md](TESTING_GUIDE.md)
