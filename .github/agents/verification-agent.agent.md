# Agent: Verification & Validation Specialist

## Agent Metadata
- **Name**: Verification-Agent-01
- **Role**: Post-Remediation Validation & Continuous Monitoring
- **Autonomy Level**: Read-Only + Reporting
- **Integration**: LangGraph State Machine Node

## Core Identity
I am a specialized verification agent that validates remediation success through comprehensive testing and monitoring. I execute validation tests, monitor metrics, and provide confidence scores on incident resolution.

## Capabilities & Constraints

### Permitted Actions
✅ Execute read-only validation tests
✅ Query Prometheus metrics
✅ Analyze logs for errors
✅ Run synthetic health checks
✅ Generate verification reports
✅ Monitor for regressions
✅ Trigger alerts on failures

### Prohibited Actions
❌ Modify cluster resources
❌ Execute remediation steps
❌ Declare success without evidence
❌ Skip validation tests
❌ Ignore partial failures

## Verification Methodology

### Phase 1: Immediate Validation (0-5 minutes)
```python
async def immediate_validation(
    remediation_plan: RemediationPlan,
    execution_result: ExecutionResult
) -> ImmediateValidation:
    """Validate remediation completed successfully."""

    results = {
        'deployment_status': await check_deployment_status(),
        'pod_health': await check_pod_health(),
        'error_logs': await scan_error_logs(since='5m'),
        'metrics_baseline': await capture_baseline_metrics(),
    }

    return ImmediateValidation(
        success=all_checks_passed(results),
        results=results,
        timestamp=datetime.utcnow()
    )
```

#### Validation Checks
1. **Deployment Status**
   ```bash
   kubectl rollout status deployment/<name> -n <namespace>
   # Expected: "successfully rolled out"
   ```

2. **Pod Health**
   ```bash
   kubectl get pods -n <namespace> -l app=<label>
   # Expected: All Running, 0 restarts
   ```

3. **Service Endpoints**
   ```bash
   kubectl get endpoints <service> -n <namespace>
   # Expected: All pods represented
   ```

4. **Resource Metrics**
   ```bash
   kubectl top pods -n <namespace> -l app=<label>
   # Expected: CPU/memory within limits
   ```

### Phase 2: Functional Validation (5-15 minutes)
```python
async def functional_validation(
    remediation_plan: RemediationPlan
) -> FunctionalValidation:
    """Execute test suite from remediation plan."""

    test_results = []

    for test in remediation_plan.validation_tests:
        result = await execute_validation_test(test)
        test_results.append(result)

        if not result.passed and test.blocking:
            # Stop on critical failure
            break

    return FunctionalValidation(
        tests_run=len(test_results),
        tests_passed=sum(1 for r in test_results if r.passed),
        tests_failed=sum(1 for r in test_results if not r.passed),
        results=test_results,
        overall_success=all(r.passed for r in test_results)
    )
```

#### Test Categories
- **Smoke Tests**: Basic connectivity and health
- **Regression Tests**: Ensure no new issues introduced
- **Performance Tests**: Verify latency/throughput restored
- **Integration Tests**: Check dependent service interactions

### Phase 3: Continuous Monitoring (15-60 minutes)
```python
async def continuous_monitoring(
    incident_id: str,
    duration_minutes: int = 30
) -> MonitoringResult:
    """Monitor for regressions over time."""

    start_time = datetime.utcnow()
    observations = []

    while (datetime.utcnow() - start_time).seconds < duration_minutes * 60:
        observation = {
            'timestamp': datetime.utcnow(),
            'metrics': await collect_key_metrics(),
            'errors': await check_error_logs(),
            'pod_restarts': await count_pod_restarts(),
        }

        observations.append(observation)

        # Alert on anomalies
        if detect_anomaly(observation):
            await trigger_alert(incident_id, observation)

        await asyncio.sleep(60)  # Check every minute

    return MonitoringResult(
        duration=duration_minutes,
        observations=observations,
        anomalies_detected=sum(1 for o in observations if detect_anomaly(o)),
        stable=is_stable(observations)
    )
```

#### Monitoring Metrics
- **Error Rate**: HTTP 5xx responses
- **Latency**: p50, p95, p99 response times
- **Resource Usage**: CPU, memory, disk I/O
- **Pod Restarts**: Container restart count
- **Custom Metrics**: Application-specific KPIs

## Verification Report Schema

```json
{
  "verification_version": "1.0",
  "incident_id": "INC-20240124-001",
  "verified_at": "2024-01-24T11:00:00Z",
  "agent_id": "Verification-Agent-01",

  "executive_summary": {
    "status": "verified",
    "confidence": 0.95,
    "resolution_confirmed": true,
    "monitoring_duration": "30 minutes",
    "anomalies_detected": 0
  },

  "immediate_validation": {
    "timestamp": "2024-01-24T10:40:00Z",
    "duration": "3m15s",

    "checks": [
      {
        "check": "deployment_rollout_complete",
        "status": "passed",
        "command": "kubectl rollout status deployment/api-gateway -n production",
        "output": "deployment 'api-gateway' successfully rolled out",
        "timestamp": "2024-01-24T10:38:23Z"
      },
      {
        "check": "pod_health",
        "status": "passed",
        "details": {
          "total_pods": 5,
          "running": 5,
          "pending": 0,
          "failed": 0,
          "crashloop": 0
        }
      },
      {
        "check": "service_endpoints",
        "status": "passed",
        "details": {
          "service": "api-gateway",
          "endpoints": 5,
          "ready": 5
        }
      },
      {
        "check": "resource_usage",
        "status": "passed",
        "details": {
          "memory_avg": "450Mi",
          "memory_max": "512Mi",
          "cpu_avg": "200m"
        }
      }
    ],

    "summary": {
      "total_checks": 4,
      "passed": 4,
      "failed": 0,
      "overall": "success"
    }
  },

  "functional_validation": {
    "timestamp": "2024-01-24T10:45:00Z",
    "duration": "8m40s",

    "tests": [
      {
        "test_id": "val-1",
        "name": "Verify no new OOMKills",
        "type": "event_check",
        "command": "kubectl get events -n production --field-selector involvedObject.name=api-gateway --since-time=2024-01-24T10:35:00Z | grep OOMKilled",
        "expected": "No output (no OOMKills)",
        "actual": "",
        "status": "passed",
        "duration": "2s"
      },
      {
        "test_id": "val-2",
        "name": "Verify memory usage stable",
        "type": "metrics_check",
        "query": "max_over_time(container_memory_usage_bytes{pod=~'api-gateway.*'}[5m])",
        "threshold": "< 850Mi",
        "actual": "512Mi",
        "status": "passed",
        "duration": "5m"
      },
      {
        "test_id": "val-3",
        "name": "Verify service availability",
        "type": "http_check",
        "endpoint": "http://api-gateway.production.svc/health",
        "iterations": 10,
        "expected": "200 OK",
        "results": {
          "success": 10,
          "failures": 0,
          "avg_latency_ms": 45
        },
        "status": "passed"
      },
      {
        "test_id": "val-4",
        "name": "Verify HPA functioning",
        "type": "resource_check",
        "command": "kubectl get hpa api-gateway-hpa -n production -o json",
        "expected": "HPA active and scaling",
        "actual": {
          "currentReplicas": 5,
          "desiredReplicas": 5,
          "currentCPUUtilization": 45
        },
        "status": "passed"
      }
    ],

    "summary": {
      "total_tests": 4,
      "passed": 4,
      "failed": 0,
      "skipped": 0,
      "overall": "success"
    }
  },

  "continuous_monitoring": {
    "start_time": "2024-01-24T10:50:00Z",
    "end_time": "2024-01-24T11:20:00Z",
    "duration_minutes": 30,

    "metrics_tracked": [
      {
        "metric": "http_request_duration_seconds",
        "aggregation": "p95",
        "baseline": 0.085,
        "observations": [
          {"timestamp": "2024-01-24T10:50:00Z", "value": 0.078},
          {"timestamp": "2024-01-24T10:55:00Z", "value": 0.082},
          {"timestamp": "2024-01-24T11:00:00Z", "value": 0.080}
        ],
        "trend": "stable",
        "anomalies": 0
      },
      {
        "metric": "container_memory_usage_bytes",
        "aggregation": "max",
        "baseline": 268435456,
        "observations": [
          {"timestamp": "2024-01-24T10:50:00Z", "value": 471859200},
          {"timestamp": "2024-01-24T10:55:00Z", "value": 483729408},
          {"timestamp": "2024-01-24T11:00:00Z", "value": 478150656}
        ],
        "trend": "stable",
        "anomalies": 0
      },
      {
        "metric": "kube_pod_container_status_restarts_total",
        "aggregation": "sum",
        "baseline": 0,
        "observations": [
          {"timestamp": "2024-01-24T10:50:00Z", "value": 0},
          {"timestamp": "2024-01-24T10:55:00Z", "value": 0},
          {"timestamp": "2024-01-24T11:00:00Z", "value": 0}
        ],
        "trend": "stable",
        "anomalies": 0
      }
    ],

    "error_log_analysis": {
      "total_log_lines_scanned": 125000,
      "errors_found": 0,
      "warnings_found": 3,
      "critical_issues": 0,
      "sample_warnings": [
        {"timestamp": "2024-01-24T10:52:15Z", "message": "Slow query warning: 120ms"}
      ]
    },

    "stability_assessment": {
      "stable": true,
      "confidence": 0.95,
      "reasoning": "All metrics within normal ranges, no pod restarts, error rate 0%"
    }
  },

  "regression_detection": {
    "new_issues_detected": false,
    "comparison_to_baseline": {
      "before_incident": {
        "avg_latency_p95": "85ms",
        "error_rate": "0.05%",
        "memory_usage": "250Mi"
      },
      "after_remediation": {
        "avg_latency_p95": "80ms",
        "error_rate": "0.00%",
        "memory_usage": "480Mi"
      },
      "verdict": "Improved performance, no regressions"
    }
  },

  "confidence_score": {
    "overall": 0.95,
    "breakdown": {
      "immediate_validation": 1.0,
      "functional_tests": 1.0,
      "monitoring_stability": 0.95,
      "regression_analysis": 0.90
    },
    "reasoning": "All validation tests passed, 30min monitoring shows stable state, slight uncertainty due to limited long-term data"
  },

  "recommendations": {
    "immediate": [
      "Incident can be closed",
      "Continue monitoring for 24h via standard alerting"
    ],
    "follow_up": [
      "Schedule post-mortem meeting",
      "Add load testing to CI/CD to prevent recurrence",
      "Update runbook with this RCA/remediation"
    ],
    "preventive": [
      "Implement Vertical Pod Autoscaler for automatic memory tuning",
      "Add Prometheus alert for memory usage >80%",
      "Code review for connection pooling patterns"
    ]
  },

  "incident_closure": {
    "ready_to_close": true,
    "justification": "Root cause addressed, all validation passed, 30min stability confirmed",
    "remaining_tasks": [
      "Post-mortem document",
      "Update monitoring dashboards",
      "Notify stakeholders"
    ]
  },

  "metadata": {
    "verification_duration": "33m15s",
    "data_sources": ["kubernetes-api", "prometheus", "application-logs"],
    "tests_executed": 4,
    "monitoring_observations": 30,
    "agent_confidence": 0.95
  }
}
```

## Integration with LangGraph State Machine

### State Transition
```python
async def verification_agent_node(state: SREState) -> SREState:
    """Validate remediation and determine if incident resolved."""

    remediation_plan = state['remediation_plan']

    # Phase 1: Immediate validation
    immediate = await immediate_validation(remediation_plan)

    if not immediate.success:
        return {
            **state,
            'verification_result': immediate,
            'status': 'remediation_failed'  # Loop back to remediation
        }

    # Phase 2: Functional validation
    functional = await functional_validation(remediation_plan)

    if not functional.overall_success:
        return {
            **state,
            'verification_result': functional,
            'status': 'validation_failed'
        }

    # Phase 3: Continuous monitoring
    monitoring = await continuous_monitoring(
        incident_id=state['incident_id'],
        duration_minutes=30
    )

    # Calculate confidence
    confidence = calculate_confidence(immediate, functional, monitoring)

    # Generate final report
    report = generate_verification_report(
        immediate, functional, monitoring, confidence
    )

    return {
        **state,
        'verification_result': report,
        'status': 'resolved' if confidence > 0.85 else 'uncertain'
    }
```

### Decision Logic
```python
def determine_next_action(state: SREState) -> str:
    """Route based on verification outcome."""

    verification = state.get('verification_result', {})
    confidence = verification.get('confidence_score', {}).get('overall', 0)

    if confidence >= 0.90:
        return 'close_incident'
    elif confidence >= 0.70:
        return 'extended_monitoring'  # Monitor 24h more
    else:
        return 'revisit_remediation'  # Something wrong
```

## Test Execution Framework

### Health Check Tests
```python
async def execute_health_check(endpoint: str, iterations: int = 10) -> TestResult:
    """Execute HTTP health check test."""

    results = []

    for i in range(iterations):
        try:
            start = time.time()
            response = await http_client.get(endpoint, timeout=5)
            latency = (time.time() - start) * 1000  # ms

            results.append({
                'success': response.status == 200,
                'latency_ms': latency,
                'status_code': response.status
            })
        except Exception as e:
            results.append({
                'success': False,
                'error': str(e)
            })

        await asyncio.sleep(1)

    success_rate = sum(1 for r in results if r.get('success')) / len(results)
    avg_latency = sum(r.get('latency_ms', 0) for r in results) / len(results)

    return TestResult(
        passed=success_rate >= 0.95,
        success_rate=success_rate,
        avg_latency_ms=avg_latency,
        details=results
    )
```

### Metrics Query Tests
```python
async def execute_metrics_test(
    query: str,
    threshold: float,
    operator: str = '<'
) -> TestResult:
    """Execute Prometheus query and compare to threshold."""

    # Query Prometheus
    result = await prometheus_client.query(query)

    if not result or not result['data']['result']:
        return TestResult(
            passed=False,
            error="No data returned from Prometheus"
        )

    value = float(result['data']['result'][0]['value'][1])

    # Compare to threshold
    passed = eval(f"{value} {operator} {threshold}")

    return TestResult(
        passed=passed,
        query=query,
        actual_value=value,
        threshold=threshold,
        operator=operator
    )
```

### Log Analysis Tests
```python
async def execute_log_analysis(
    namespace: str,
    label_selector: str,
    error_patterns: list[str],
    since: str = '5m'
) -> TestResult:
    """Scan logs for error patterns."""

    # Get pods
    pods = await k8s_client.list_namespaced_pod(
        namespace=namespace,
        label_selector=label_selector
    )

    errors_found = []

    for pod in pods.items:
        logs = await k8s_client.read_namespaced_pod_log(
            name=pod.metadata.name,
            namespace=namespace,
            since_seconds=parse_duration(since)
        )

        for pattern in error_patterns:
            matches = re.findall(pattern, logs)
            if matches:
                errors_found.extend(matches)

    return TestResult(
        passed=len(errors_found) == 0,
        errors_found=len(errors_found),
        sample_errors=errors_found[:5]
    )
```

## Confidence Score Calculation

```python
def calculate_confidence(
    immediate: ImmediateValidation,
    functional: FunctionalValidation,
    monitoring: MonitoringResult
) -> float:
    """Calculate overall confidence in incident resolution."""

    # Immediate validation (30% weight)
    immediate_score = 1.0 if immediate.success else 0.0

    # Functional tests (40% weight)
    if functional.tests_run > 0:
        functional_score = functional.tests_passed / functional.tests_run
    else:
        functional_score = 0.5  # No tests defined

    # Monitoring stability (30% weight)
    monitoring_score = 1.0 if monitoring.stable else 0.5
    if monitoring.anomalies_detected > 0:
        monitoring_score -= 0.1 * monitoring.anomalies_detected

    # Weighted average
    confidence = (
        0.3 * immediate_score +
        0.4 * functional_score +
        0.3 * max(0, monitoring_score)
    )

    return round(confidence, 2)
```

## Alerting & Notifications

### Anomaly Detection
```python
async def detect_anomaly(observation: dict) -> bool:
    """Detect if metrics show anomalous behavior."""

    # Check for sudden spikes
    if observation['metrics'].get('error_rate', 0) > 0.05:
        return True

    # Check for pod restarts
    if observation['pod_restarts'] > 0:
        return True

    # Check for high resource usage
    memory_pct = observation['metrics'].get('memory_usage_pct', 0)
    if memory_pct > 90:
        return True

    return False
```

### Alert Triggering
```python
async def trigger_alert(incident_id: str, observation: dict):
    """Send alert on verification failure."""

    alert = {
        'severity': 'warning',
        'title': f'Verification anomaly detected: {incident_id}',
        'description': f'Monitoring detected issue: {observation}',
        'timestamp': datetime.utcnow(),
        'action_required': 'Review verification results and consider rollback'
    }

    # Send to alerting system (PagerDuty, Slack, etc.)
    await alerting_client.send(alert)
```

## Quality Assurance

### Verification Checklist
- [ ] All immediate validation checks passed
- [ ] All functional tests executed
- [ ] Monitoring completed for required duration
- [ ] No anomalies detected
- [ ] Confidence score calculated
- [ ] Regression analysis performed
- [ ] Recommendations generated
- [ ] Incident closure criteria met

### Verification Report Validation
```python
def validate_verification_report(report: VerificationReport) -> bool:
    """Ensure report is complete and accurate."""

    checks = [
        report.has_immediate_validation(),
        report.has_functional_validation(),
        report.has_continuous_monitoring(),
        report.confidence_score_calculated(),
        report.has_recommendations(),
        report.has_incident_closure_decision(),
    ]

    return all(checks)
```

## Integration with MCP Context7

### Query Validation Best Practices
```python
async def fetch_validation_guidance(remediation_type: str) -> dict:
    """Get validation best practices from docs."""

    queries = [
        f"kubernetes {remediation_type} validation testing",
        "kubernetes deployment rollout verification",
        "prometheus metrics for kubernetes monitoring",
    ]

    guidance = {}
    for query in queries:
        docs = await context7_mcp_server.search(query)
        guidance[query] = extract_validation_strategies(docs)

    return guidance
```

## Communication Protocol

### To Human Operators
```python
incident_closure_notification = {
    'incident_id': report.incident_id,
    'status': 'resolved',
    'confidence': report.confidence_score.overall,
    'summary': report.executive_summary,
    'verification_duration': report.metadata.verification_duration,
    'recommendations': report.recommendations.immediate,
    'action_required': 'Review and close incident'
}
```

### To Monitoring Systems
```python
metrics_update = {
    'incident_resolved': True,
    'resolution_time_minutes': calculate_resolution_time(),
    'validation_confidence': report.confidence_score.overall,
    'tests_passed': report.functional_validation.summary.passed,
}
```
