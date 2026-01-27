#!/bin/bash
# Complete AEGIS test suite runner
# Tests all components: unit tests, integration tests, Docker, observability, CLI

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
START_TIME=$(date +%s)

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Main test suite
main() {
    print_header "🧪 AEGIS Complete Test Suite"

    echo "Starting comprehensive testing..."
    echo "Test date: $(date)"
    echo ""

    # ========================================================================
    # 1. UNIT TESTS
    # ========================================================================
    print_header "1️⃣  Unit Tests"

    if make test-unit > /tmp/aegis_unit_tests.log 2>&1; then
        UNIT_COUNT=$(grep -o "passed" /tmp/aegis_unit_tests.log | wc -l | tr -d ' ')
        print_success "Unit tests passed ($UNIT_COUNT tests)"
    else
        print_failure "Unit tests failed - see /tmp/aegis_unit_tests.log"
        tail -20 /tmp/aegis_unit_tests.log
        exit 1
    fi

    # ========================================================================
    # 2. INTEGRATION TESTS
    # ========================================================================
    print_header "2️⃣  Integration Tests"

    if make test-integration > /tmp/aegis_integration_tests.log 2>&1; then
        INT_COUNT=$(grep -o "passed" /tmp/aegis_integration_tests.log | wc -l | tr -d ' ')
        print_success "Integration tests passed ($INT_COUNT tests)"
    else
        print_failure "Integration tests failed - see /tmp/aegis_integration_tests.log"
        tail -20 /tmp/aegis_integration_tests.log
        exit 1
    fi

    # ========================================================================
    # 3. DOCKER BUILD
    # ========================================================================
    print_header "3️⃣  Docker Build Test"

    if docker build -t aegis-operator:test -f deploy/docker/Dockerfile . > /tmp/aegis_docker_build.log 2>&1; then
        print_success "Docker build passed"
    else
        print_failure "Docker build failed - see /tmp/aegis_docker_build.log"
        tail -20 /tmp/aegis_docker_build.log
        exit 1
    fi

    # ========================================================================
    # 4. OBSERVABILITY STACK
    # ========================================================================
    print_header "4️⃣  Observability Stack Test"

    print_info "Starting docker-compose services..."
    docker compose -f deploy/docker/docker-compose.yaml up -d > /tmp/aegis_compose.log 2>&1

    print_info "Waiting for services to be ready (15s)..."
    sleep 15

    # Test Prometheus
    if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
        print_success "Prometheus healthy"
    else
        print_failure "Prometheus not responding"
        docker logs aegis-prometheus --tail 20
        exit 1
    fi

    # Test Grafana
    if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
        print_success "Grafana healthy"
    else
        print_failure "Grafana not responding"
        docker logs aegis-grafana --tail 20
        exit 1
    fi

    # Test Loki
    if curl -sf http://localhost:3100/ready > /dev/null 2>&1; then
        print_success "Loki healthy"
    else
        print_failure "Loki not responding"
        docker logs aegis-loki --tail 20
        exit 1
    fi

    # ========================================================================
    # 5. ALERT RULES VALIDATION
    # ========================================================================
    print_header "5️⃣  Alert Rules Validation"

    # Check if alert rules loaded
    ALERT_COUNT=$(curl -s http://localhost:9090/api/v1/rules | jq '[.data.groups[].rules[]] | length' 2>/dev/null || echo "0")

    if [ "$ALERT_COUNT" -eq 15 ]; then
        print_success "Alert rules loaded (15/15)"
    else
        print_failure "Alert rules mismatch: expected 15, found $ALERT_COUNT"
        curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
        exit 1
    fi

    # List alert groups
    print_info "Alert groups:"
    curl -s http://localhost:9090/api/v1/rules | jq -r '.data.groups[].name' | sed 's/^/  - /'

    # ========================================================================
    # 6. CLI SMOKE TEST
    # ========================================================================
    print_header "6️⃣  CLI Smoke Test"

    print_info "Testing CLI analysis with mock data..."
    if uv run aegis analyze pod/test-pod --namespace default --mock > /tmp/aegis_cli_output.txt 2>&1; then
        print_success "CLI analysis completed"
    else
        print_failure "CLI analysis failed"
        cat /tmp/aegis_cli_output.txt
        exit 1
    fi

    # Verify verbose output
    VERBOSE_CHECKS=0

    if grep -q "Step-by-Step Analysis" /tmp/aegis_cli_output.txt; then
        print_success "Verbose output: analysis_steps present"
        ((VERBOSE_CHECKS++))
    else
        print_failure "Verbose output: analysis_steps missing"
    fi

    if grep -q "Evidence Summary" /tmp/aegis_cli_output.txt; then
        print_success "Verbose output: evidence_summary present"
        ((VERBOSE_CHECKS++))
    else
        print_failure "Verbose output: evidence_summary missing"
    fi

    if grep -q "Decision Rationale" /tmp/aegis_cli_output.txt; then
        print_success "Verbose output: decision_rationale present"
        ((VERBOSE_CHECKS++))
    else
        print_failure "Verbose output: decision_rationale missing"
    fi

    if [ "$VERBOSE_CHECKS" -ne 3 ]; then
        echo ""
        echo "CLI output sample:"
        head -50 /tmp/aegis_cli_output.txt
        exit 1
    fi

    # ========================================================================
    # 7. GRAFANA DATASOURCES
    # ========================================================================
    print_header "7️⃣  Grafana Datasources"

    DATASOURCES=$(curl -s -u admin:aegis123 http://localhost:3000/api/datasources 2>/dev/null | jq length)

    if [ "$DATASOURCES" -ge 2 ]; then
        print_success "Grafana datasources configured ($DATASOURCES)"
        curl -s -u admin:aegis123 http://localhost:3000/api/datasources | \
            jq -r '.[] | "  - \(.name) (\(.type))"'
    else
        print_failure "Grafana datasources missing"
        exit 1
    fi

    # ========================================================================
    # 8. DOCKER COMPOSE PS
    # ========================================================================
    print_header "8️⃣  Container Status"

    docker compose -f deploy/docker/docker-compose.yaml ps

    # ========================================================================
    # CLEANUP
    # ========================================================================
    print_header "🧹 Cleanup"

    print_info "Stopping docker-compose services..."
    docker compose -f deploy/docker/docker-compose.yaml down > /dev/null 2>&1
    print_success "Cleanup complete"

    # ========================================================================
    # SUMMARY
    # ========================================================================
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    print_header "📊 Test Summary"

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    All Tests Passed! ✅                      ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  Test Results:                                               ║${NC}"
    echo -e "${GREEN}║    ✅ Unit Tests                                             ║${NC}"
    echo -e "${GREEN}║    ✅ Integration Tests                                      ║${NC}"
    echo -e "${GREEN}║    ✅ Docker Build                                           ║${NC}"
    echo -e "${GREEN}║    ✅ Observability Stack (Prometheus, Grafana, Loki)        ║${NC}"
    echo -e "${GREEN}║    ✅ Alert Rules (15/15)                                    ║${NC}"
    echo -e "${GREEN}║    ✅ CLI Verbose Output                                     ║${NC}"
    echo -e "${GREEN}║    ✅ Grafana Datasources                                    ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║  Duration: ${DURATION}s                                           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🏆 AEGIS is ready for hackathon submission!${NC}"
    echo ""
    echo "Logs saved to /tmp/aegis_*.log"
    echo ""
}

# Run main function
main "$@"
