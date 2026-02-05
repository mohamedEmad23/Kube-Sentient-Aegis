# AEGIS Incident Response Runbook

**Version**: 2.0
**Last Updated**: 2026-02-05
**Audience**: SRE Team, Platform Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Incident Detection](#incident-detection)
3. [Queue Management](#queue-management)
4. [Shadow Verification](#shadow-verification)
5. [Production Deployment](#production-deployment)
6. [Rollback Procedures](#rollback-procedures)
7. [Troubleshooting](#troubleshooting)
8. [Metrics & Monitoring](#metrics--monitoring)

---

## Overview

AEGIS is an autonomous SRE agent that detects, analyzes, and remediates Kubernetes incidents using AI-powered analysis and shadow verification. This runbook provides step-by-step procedures for incident response.

### System Architecture

```
Incident Detection → Queue (P0-P4) → RCA → Solution → Shadow Verification → Human Approval → Production Deployment → Rollback Monitor
```

### Key Components

- **Incident Queue**: Priority-based processing (P0-P4)
- **RCA Agent**: Root cause analysis (Groq)
- **Solution Agent**: Fix proposal generation (Gemini)
- **Shadow Manager**: Isolated test environments (vCluster)
- **Security Gates**: Pre-deployment vulnerability scanning
- **Rollback Agent**: Automatic rollback on error spikes

---

## Incident Detection

### Automatic Detection

AEGIS monitors Pod and Deployment events via Kopf handlers:

- **P0 (Critical)**: Pod Failed/Unknown, Deployment >75% unavailable
- **P1 (High)**: CrashLoopBackOff, Deployment 50-75% unavailable
- **P2 (Medium)**: Deployment 25-50% unavailable
- **P3 (Low)**: Intermittent failures
- **P4 (Info)**: Background issues

**Monitoring**:
```bash
# Watch operator logs
kubectl logs -f deployment/aegis-operator -n aegis-system

# Check K8sGPT Results
kubectl get results.core.k8sgpt.ai -A
```

### Manual Triggering

Manually analyze a resource:

```bash
# Analyze a deployment
aegis analyze deployment/api -n production

# Analyze a pod
aegis analyze pod/worker-xyz -n production
```

---

## Queue Management

### Check Queue Status

```bash
aegis queue status
```

**Output**:
- Production lock status
- Queue depth by priority (P0-P4)
- Summary statistics

**Interpreting Results**:
- **P0 incidents lock production** → No deployments until resolved
- High P0 depth → Critical issues need immediate attention
- Queue backlog → May need to scale incident processors

### Production Lock

**What it means**:
When a P0 incident is detected, production deployments are automatically locked to prevent cascading failures.

**Unlock manually** (use with caution):
```bash
aegis queue unlock

# Force unlock without confirmation
aegis queue unlock --force
```

> [!CAUTION]
> Only unlock production if you're certain the blocking P0 incident has been resolved.

---

## Shadow Verification

### Monitor Shadow Environments

```bash
# List all shadows
aegis shadow list

# Check shadow status
aegis shadow status <shadow-id>

# Wait for shadow readiness
aegis shadow wait <shadow-id> --timeout 300
```

### Shadow Verification Flow

1. **Creation**: vCluster spins up (~30-60s)
2. **Drift Detection**: Compare prod vs shadow config
3. **Fix Application**: Apply proposed changes
4. **Security Scan**: Kubesec vulnerability check
5. **Smoke Tests**: Basic health checks
6. **Load Tests**: P99 latency validation

### Manual Shadow Creation

```bash
# Create shadow for deployment
aegis shadow create deployment/api -n production --wait

# Delete shadow when done
aegis shadow delete <shadow-id>
```

---

## Production Deployment

### Approval Process

When shadow verification completes, you'll see a terminal prompt:

```
===============================================================================
SHADOW VERIFICATION COMPLETED - PRODUCTION APPROVAL REQUIRED
===============================================================================

Incident ID: incident-abc-123
Resource: Deployment/api
Namespace: production

FIX PROPOSAL:
  Type: ConfigChange
  Description: Update database connection pool size
  Confidence: 92.5%

SHADOW VERIFICATION RESULTS:
  ✓ Security Scans: PASSED
  ✓ Smoke Tests: PASSED (5/5)
  ✓ Load Tests: PASSED (p99: 45ms)

===============================================================================

Apply fix to production? [yes/no]:
```

### Pre-Deployment Checks

Before typing `yes`, verify:

1. **Shadow results** all passed
2. **Fix description** makes sense
3. **Confidence score** >80%
4.  **No critical vulnerabilities**
5. **Production not locked**

### Deployment Gates

The system automatically blocks deployments if:

- **Production is locked** (P0 incident active)
- **Critical CVEs detected** (security scan failed)
- **Shadow verification failed**

---

## Rollback Procedures

### Automatic Rollback

AEGIS monitors production for 5 minutes after deployment:

- **Trigger**: Error rate spike >20% above baseline
- **Action**: Automatic rollback to pre-deployment snapshot
- **Notification**: Logs + metrics

**Monitoring**:
```bash
# Watch for rollback events
kubectl logs -f deployment/aegis-operator -n aegis-system | grep rollback
```

### Manual Rollback

```bash
aegis rollback deployment/api --snapshot snapshot-20260204-123456 -n production
```

> [!WARNING]
> Manual rollback requires snapshot ID. Snapshots are currently stored in memory during incident lifecycle. Check operator logs for snapshot details.

### Rollback Verification

After rollback (auto or manual):

1. **Check deployment status**: `kubectl get deployment/api -n production`
2. **Verify pod health**: `kubectl get pods -n production -l app=api`
3. **Monitor error rates**: Check Grafana dashboard
4. **Alert stakeholders**: Post in incident channel

---

## Troubleshooting

### Issue: Incidents Not Processing

**Symptoms**:
- Queue depth increasing
- No logs from processor daemon

**Diagnosis**:
```bash
# Check operator status
aegis operator status

# Check processor daemon
kubectl logs deployment/aegis-operator -n aegis-system | grep processor
```

**Solutions**:
1. Verify operator is running: `kubectl get deployment aegis-operator -n aegis-system`
2. Check LLM connectivity:
   - Groq API key configured
   - Gemini API key configured
   - Ollama reachable
3. Restart operator: `kubectl rollout restart deployment/aegis-operator -n aegis-system`

---

### Issue: Shadow Verification Failing

**Symptoms**:
- Shadow status stuck in `creating` or `testing`
- Verification timeout errors

**Diagnosis**:
```bash
# Check shadow status
aegis shadow list

# View shadow logs
aegis shadow status <shadow-id>

# Check drift detection
kubectl logs deployment/aegis-operator -n aegis-system | grep drift
```

**Solutions**:
1. **Drift detected**: Review `drift_report` in shadow status
   - High drift severity → Shadow config doesn't match production
   - Fix: Update shadow creation logic or production baseline

2. **vCluster creation failed**:
   - Check vCluster availability: `kubectl get pods -n vcluster-system`
   - Verify DNS resolution in shadow namespace

3. **Security scan blocking**:
   - Check for Critical CVEs in shadow logs
   - Fix: Update images to patched versions

4. **Cleanup and retry**:
   ```bash
   aegis shadow delete <shadow-id> --force
   # Operator will retry automatically
   ```

---

### Issue: Production Lock Won't Clear

**Symptoms**:
- P0 incident resolved but production still locked
- Cannot deploy approved fixes

**Diagnosis**:
```bash
aegis queue status
```

**Solutions**:
1. **Verify P0 incident is marked resolved**:
   ```bash
   kubectl get results.core.k8sgpt.ai -A | grep -v Resolved
   ```

2. **Manual unlock** (last resort):
   ```bash
   aegis queue unlock --force
   ```

3. **Check processor daemon**:
   - May not be processing queue correctly
   - Restart operator to reinitialize

---

### Issue: Rollback Not Triggering

**Symptoms**:
- Error rate spike but no automatic rollback
- Deployment in degraded state

**Diagnosis**:
```bash
# Check rollback monitoring logs
kubectl logs deployment/aegis-operator -n aegis-system | grep rollback_agent

# Check error rate metrics
curl http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])
```

**Solutions**:
1. **Rollback disabled**: Check `settings.observability.rollback_enabled`
2. **Prometheus unavailable**: Verify Prometheus connectivity
3. **Error rate below threshold**: 20% spike required for auto-rollback
4. **Manual rollback**:
   ```bash
   # Check logs for snapshot ID
   kubectl logs deployment/aegis-operator -n aegis-system | grep snapshot

   # Execute manual rollback
   aegis rollback deployment/api --snapshot <snapshot-id> -n production
   ```

---

## Metrics & Monitoring

### Key Prometheus Metrics

**Incident Queue**:
```promql
aegis_incident_queue_depth{priority="p0"}
aegis_incident_queue_enqueued_total{priority="p1"}
aegis_incident_queue_correlated_total
```

**Shadow Verification**:
```promql
aegis_shadow_retries_total{outcome="success", attempt="2"}
aegis_drift_detections_total{severity="high"}
```

**Security**:
```promql
aegis_security_blocks_total{scan_type="kubesec", severity="CRITICAL"}
```

**Rollback**:
```promql
aegis_rollbacks_total{reason="error_rate_spike"}
aegis_rollback_success_total
```

### Grafana Dashboards

1. **Incident Response Overview**
   - Queue depth by priority
   - MTTR (Mean Time To Resolution)
   - Success rate

2. **Rollback Monitoring**
   - Rollback frequency
   - Error rate pre/post deployment
   - Recovery time

3. **Security Gate Status**
   - Block rate by scanner
   - Top blocked CVEs

**Access**: `http://grafana:3000/dashboards`

---

## Escalation

### When to Escalate

Escalate to platform team if:

- **Multiple P0 incidents** in different namespaces (potential cluster issue)
- **Shadow verification consistently failing** (infrastructure problem)
- **Rollback failures** (may indicate data corruption)
- **Security gates blocking all deployments** (widespread vulnerability)

### Escalation Contacts

- **Platform Team**: `#platform-oncall` Slack
- **Security Team**: `#security-incidents` Slack
- **Page SRE Lead**: Use PagerDuty

---

## Appendix

### Configuration Reference

Key settings in `.env` or ConfigMap:

```bash
# Rollback
OBSERVABILITY__ROLLBACK_ENABLED=true
OBSERVABILITY__ROLLBACK_ERROR_RATE_THRESHOLD=0.20
OBSERVABILITY__ROLLBACK_MONITORING_WINDOW_MINUTES=5

# Shadow
SHADOW__RUNTIME=vcluster
SHADOW__AUTO_CLEANUP=true
SHADOW__VERIFICATION_TIMEOUT=300

# LLM
AGENT__RCA_PROVIDER=groq
AGENT__SOLUTION_PROVIDER=gemini
```

### Useful Commands Cheat Sheet

```bash
# Queue
aegis queue status                          # Check queue + production lock
aegis queue unlock --force                 # Manually unlock production

# Shadow
aegis shadow list                          # List all shadows
aegis shadow status <id>                    # Shadow details
aegis shadow delete <id> --force           # Force cleanup

# Rollback
aegis rollback deployment/app -s <snapshot-id> -n prod

# Analysis
aegis analyze deployment/app -n prod       # Manual incident analysis

# Operator
aegis operator status                      # Check cluster connectivity
aegis operator run -n production           # Run operator (local dev)
```

---

**End of Runbook**
