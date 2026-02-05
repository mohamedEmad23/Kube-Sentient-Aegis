# AEGIS Demo Scenarios - Hackathon Presentation

**Purpose**: Live demonstrations of the Enhanced AI-SRE Incident Response System
**Duration**: 15-20 minutes
**Environment**: Kind cluster with AEGIS operator running

---

## Setup Prerequisites

```bash
# 1. Start AEGIS operator
kubectl apply -f deploy/operator.yaml

# 2. Verify operator is running
kubectl logs -f deploy/aegis-operator | grep "incident_queue_processor"

# 3. Open Grafana dashboard
# URL: http://localhost:3000/d/aegis-incident-response

# 4. Open Prometheus
# URL: http://localhost:9090
```

---

## Demo 1: Simple CrashLoopBackOff with Auto-Remediation

**Objective**: Show basic incident detection → queue → analysis → shadow → approval → production → resolution

###  Step 1: Deploy Broken Application

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: demo
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-app
  namespace: demo
  annotations:
    aegis.io/monitor: "enabled"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: broken-app
  template:
    metadata:
      labels:
        app: broken-app
    spec:
      containers:
      - name: app
        image: nginx:alpine
        envFrom:
        - configMapRef:
            name: app-config  # Missing ConfigMap → CrashLoopBackOff
EOF
```

### Step 2: Watch AEGIS Detect Incident

```bash
# Terminal 1: Watch operator logs
kubectl logs -f deploy/aegis-operator | grep broken-app

# Expected output:
# 🔍 Enqueuing pod incident for analysis
# ✅ Incident enqueued: inc-20260204-235900-demo-broken-app-xyz
# Priority: p1
```

### Step 3: Observe Queue Metrics

```bash
# Open Prometheus: http://localhost:9090
# Query:
aegis_incident_queue_depth{priority="p1"}
# Expected: 1

aegis_incident_queue_enqueued_total{priority="p1"}
# Expected: Incremented by 1
```

### Step 4: Watch Incident Processing

```bash
# Terminal 1: Operator logs
# Expected output:
# 📨 Dequeued incident for processing
# incident_id: inc-20260204-235900-demo-broken-app-xyz
# 🤖 RCA Agent analyzing...
# ✅ RCA completed: Missing ConfigMap 'app-config'
# 🔧 Solution Agent proposing fix...
# ✅ Fix proposed: Create ConfigMap with defaults
```

### Step 5: Shadow Verification

```bash
# Watch shadow creation
kubectl get ns | grep shadow-

# Expected: shadow-abc123 namespace created

# Watch shadow logs
kubectl logs -f deploy/aegis-operator | grep shadow

# Expected:
# Creating shadow environment...
# ✅ Security scan passed (Kubesec)
# Running smoke tests...
# ✅ Smoke tests passed (5/5)
# Shadow verification PASSED
```

### Step 6: Human Approval

```bash
# Terminal shows:
================================================================================
SHADOW VERIFICATION COMPLETED - PRODUCTION APPROVAL REQUIRED
================================================================================

Incident ID: inc-20260204-235900-demo-broken-app-xyz
Resource: Deployment/broken-app
Namespace: demo

FIX PROPOSAL:
  Type: config_change
  Description: Create ConfigMap 'app-config' with default values
  Confidence: 94.2%

SHADOW VERIFICATION RESULTS:
  ✓ Security Scans: PASSED
  ✓ Smoke Tests: PASSED (5/5)

================================================================================

Apply fix to production? [yes/no]:
```

**Type**: `yes` <Enter>

### Step 7: Production Deployment + Rollback Monitoring

```bash
# Watch production apply
kubectl get configmap -n demo app-config
# Expected: ConfigMap created

kubectl get pods -n demo
# Expected: Pods running

# Operator logs:
# ✅ Fix applied to production
# 🔍 Rollback agent monitoring (5min window)...
# Baseline error rate: 0.0%
# Current error rate: 0.0%
# ✅ Stable - No rollback needed
# ✅ Incident resolved
```

### Demo 1 Success Criteria

- ✅ Incident detected and enqueued with P1 priority
- ✅ RCA correctly identified missing ConfigMap
- ✅ Solution created ConfigMap with defaults
- ✅ Shadow verification passed
- ✅ Human approval prompted
- ✅ Production fix applied successfully
- ✅ Rollback agent confirmed stability
- ✅ Total time: ~3-5 minutes

---

## Demo 2: Shadow Retry Logic with Transient Failure

**Objective**: Show shadow verification retry with exponential backoff

### Step 1: Deploy App with Tight Memory Limits

```bash
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-hungry
  namespace: demo
  annotations:
    aegis.io/monitor: "enabled"
spec:
  replicas: 2
  selector:
    matchLabels:
      app: memory-hungry
  template:
    metadata:
      labels:
        app: memory-hungry
    spec:
      containers:
      - name: app
        image: nginx:alpine
        resources:
          limits:
            memory: "10Mi"  # Too low → OOMKilled
EOF
```

### Step 2: Watch AI Propose Insufficient Fix

```bash
# Operator logs:
# ✅ RCA: OOMKilled - memory limit too low
# 🔧 Solution: Increase memory to 50Mi  # Still too low!
```

### Step 3: Shadow Verification Fails (Attempt 1)

```bash
# Operator logs:
# Creating shadow environment...
# Applying fix (memory: 50Mi)...
# ❌ Shadow pod OOMKilled
# 🔄 Retry 1/3 - Backoff: 10s
```

### Step 4: Solution Agent Refines Fix (Attempt 2)

```bash
# After 10s backoff:
# 🔧 Solution: Increase memory to 128Mi  # Better
# Creating shadow environment...
# ❌ Shadow pod still crashing
# 🔄 Retry 2/3 - Backoff: 30s
```

### Step 5: Final Attempt (Attempt 3)

```bash
# After 30s backoff:
# 🔧 Solution: Increase memory to 256Mi + add readiness probe
# Creating shadow environment...
# ✅ Shadow verification PASSED
```

### Demo 2 Success Criteria

- ✅ Shadow failed on first attempt (10Mi memory)
- ✅ Exponential backoff observed (10s, 30s)
- ✅ Solution agent refined fix based on failure context
- ✅ Final attempt succeeded
- ✅ Metrics: `aegis_shadow_retries_total{outcome="success",attempt="3"}` incremented

---

## Demo 3: Auto-Rollback on Production Degradation

**Objective**: Demonstrate automated rollback when production error rate spikes

### Step 1: Deploy Working Application

```bash
kubectl apply -f examples/demo-app/working.yaml
# Wait for stable baseline: 5xx error rate = 0%
```

### Step 2: Inject Misconfiguration

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: demo
data:
  API_ENDPOINT: "https://invalid-endpoint.example.com"  # Broken
  TIMEOUT: "1s"  # Too short
EOF

kubectl rollout restart deployment/demo-app -n demo
```

### Step 3: Watch Error Rate Spike

```bash
# Prometheus query:
rate(http_requests_total{status=~"5.."}[1m])

# Expected: Spike from 0% → 45%
```

### Step 4: Rollback Agent Triggers

```bash
# Operator logs (within 2 minutes):
# 🔍 Rollback agent monitoring...
# Baseline error rate: 0.0%
# Current error rate: 45.2%
# 🚨 ERROR RATE SPIKE DETECTED (>20%)
# 🔄 Executing auto-rollback...
# Applying pre-deployment snapshot...
# ✅ Rollback completed (15.2s)
# Current error rate: 0.1%
#  � Alerting: Rollback executed
```

### Step 5: Verify Rollback

```bash
kubectl get configmap app-config -n demo -o yaml

# Expected: Original values restored
data:
  API_ENDPOINT: "https://api.example.com"
  TIMEOUT: "30s"
```

### Demo 3 Success Criteria

- ✅ Baseline error rate captured (0%)
- ✅ Degradation detected within 2 minutes
- ✅ Auto-rollback triggered
- ✅ Original config restored
- ✅ Error rate returned to normal
- ✅ Metrics: `aegis_rollbacks_total{reason="error_rate_spike"}` incremented

---

## Demo 4: Security Gate Blocking Critical CVEs

**Objective**: Show pre-deployment security blocking

### Step 1: Trigger Incident with Vulnerable Image

```bash
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vuln-app
  namespace: demo
  annotations:
    aegis.io/monitor: "enabled"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vuln-app
  template:
    metadata:
      labels:
        app: vuln-app
    spec:
      containers:
      - name: app
        image: vulnerable/log4j:2.14.0  # Critical CVE-2021-44228
EOF
```

### Step 2: AI Proposes Fix (Upgrade Image)

```bash
# Operator logs:
# ✅ RCA: CrashLoopBackOff
# 🔧 Solution: Upgrade image to log4j:2.17.0
```

### Step 3: Security Gate Blocks Deployment

```bash
# Operator logs:
# 🔍 Running pre-shadow security scan...
# ❌ SECURITY BLOCK: 1 Critical vulnerability
#   - CVE-2021-44228: Log4j RCE vulnerability (CVSS 10.0)
# Shadow deployment BLOCKED
# 🔄 Returning to Solution Agent for fix refinement
```

### Step 4: Solution Agent Refines Fix

```bash
# Solution Agent:
# 🔧 Refined solution: Use secure alternative: nginx:alpine
# 🔍 Running security scan...
# ✅ Security scan passed
# Proceeding to shadow verification...
```

### Demo 4 Success Criteria

- ✅ Initial fix (log4j:2.17.0) blocked by security gate
- ✅ Critical CVE-2021-44228 detected
- ✅ Metric: `aegis_security_blocks_total{severity="CRITICAL"}` incremented
- ✅ Solution agent refined to secure image (nginx)
- ✅ Second attempt passed security scan

---

## Demo 5: Priority Queue with P0 Production Lock

**Objective**: Show P0 incidents preempt other work and lock production

### Step 1: Create Multiple Incidents

```bash
# Create P3 incident (low priority)
kubectl delete configmap low-priority -n demo
kubectl rollout restart deployment/low-priority-app -n demo

# Create P2 incident (medium priority)
kubectl scale deployment medium-priority-app -n demo --replicas=1

# Create P0 incident (critical - all replicas down)
kubectl delete deployment critical-app -n demo --cascade=orphan
```

### Step 2: Watch Queue Prioritization

```bash
# Prometheus queries:
aegis_incident_queue_depth{priority="p0"}  # Expected: 1
aegis_incident_queue_depth{priority="p2"}  # Expected: 1
aegis_incident_queue_depth{priority="p3"}  # Expected: 1

# Operator logs:
# 📨 Dequeued incident: P0 (critical-app)  # P0 first!
# 🔒 Production locked: P0 incident active
```

### Step 3: Verify Production Lock

```bash
# Try to manually approve a different incident
# Terminal shows:
# ❌ Production deployment locked
# Lock reason: P0 incident detected: inc-xyz
# Deployment blocked until P0 resolved
```

### Step 4: P0 Resolution Unlocks Production

```bash
# After P0 is resolved:
# ✅ P0 incident resolved
# 🔓 Production unlocked
# 📨 Dequeued incident: P2 (medium-priority-app)
```

### Demo 5 Success Criteria

- ✅ P0 incident processed first (bypassing P2/P3 in queue)
- ✅ Production automatically locked when P0 detected
- ✅ Other incidents blocked until P0 resolved
- ✅ Production unlocked after P0 resolution
- ✅ P2 incident processed next (correct priority order)

---

## Walkthrough Script for Presenter

**Total Time**: 18 minutes

1. **Introduction** (2 min)
   - "AEGIS is an AI-driven incident response system with 9 verification layers"
   - Show architecture diagram
   - Highlight key features (queue, rollback, security gates)

2. **Demo 1: Happy Path** (4 min)
   - Deploy broken app
   - Show detection → queue → RCA → solution → shadow → approval
   - Highlight human approval gate
   - Show production deployment + rollback monitoring

3. **Demo 2: Retry Logic** (3 min)
   - Show shadow failure with insufficient memory
   - Highlight exponential backoff (10s, 30s)
   - Show solution refinement
   - Final success on attempt 3

4. **Demo 3: Auto-Rollback** (4 min)
   - Deploy working app
   - Inject bad config
   - Show error rate spike in Prometheus
   - Highlight auto-rollback within 2 minutes
   - Show config restored

5. **Demo 4: Security Gate** (3 min)
   - Trigger incident with vulnerable image
   - Show security block on Critical CVE
   - Highlight solution refinement
   - Show second attempt with secure image

6. **Demo 5: Priority Queue** (2 min)
   - Create P0, P2, P3 incidents
   - Show P0 processed first
   - Highlight production lock
   - Show unlock after P0 resolution

7. **Q&A** (Remaining time)

---

## Cleanup

```bash
# Delete demo resources
kubectl delete ns demo

# Verify queue is empty
# Prometheus: aegis_incident_queue_depth{priority=~".*"} == 0
```

---

## Tips for Successful Demo

1. **Pre-stage commands** - Have all kubectl commands ready in text file
2. **Split terminal** - Show operator logs + kubectl commands side-by-side
3. **Prometheus open** - Keep Grafana/Prometheus dashboards visible
4. **Backup plan** - If live demo fails, have recorded video
5. **Practice timing** - Run through demos multiple times to hit 18-minute target
6. **Highlight metrics** - Point out Prometheus counters incrementing in real-time

---

**Good luck with the hackathon presentation! 🚀**
