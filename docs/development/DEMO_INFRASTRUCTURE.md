# AEGIS Demo Infrastructure Guide

## Overview

This document describes the complete demo infrastructure for testing and demonstrating AEGIS capabilities. It answers the critical questions:

1. **What application does AEGIS analyze?** → A purpose-built demo app with intentional failure scenarios
2. **How do we create failure scenarios?** → Pre-configured manifests that simulate real-world incidents
3. **How does shadow verification work?** → vCluster creates isolated environments to test fixes
4. **What does the RCA report analyze?** → Real Kubernetes events, pod states, and logs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LOCAL DEVELOPMENT MACHINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     KIND CLUSTER (aegis-demo)                        │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │   │
│  │  │   PRODUCTION    │  │   MONITORING    │  │   SHADOW ENV        │   │   │
│  │  │   NAMESPACE     │  │   NAMESPACE     │  │   (vCluster)        │   │   │
│  │  ├─────────────────┤  ├─────────────────┤  ├─────────────────────┤   │   │
│  │  │ demo-api        │  │ prometheus      │  │ ┌─────────────────┐ │   │   │
│  │  │ demo-worker     │  │ grafana         │  │ │ Cloned workload │ │   │   │
│  │  │ demo-db         │  │ loki            │  │ │ + proposed fix  │ │   │   │
│  │  │ demo-redis      │  │                 │  │ └─────────────────┘ │   │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │                    AEGIS OPERATOR NAMESPACE                      │ │   │
│  │  ├─────────────────────────────────────────────────────────────────┤ │   │
│  │  │ aegis-operator  │  aegis-agent  │  incident CRDs  │  shadow CRDs│ │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────────────┐   │
│  │    OLLAMA     │  │    K8sGPT     │  │       AEGIS CLI               │   │
│  │  (localhost)  │  │    (CLI)      │  │  aegis analyze pod/demo-api   │   │
│  └───────────────┘  └───────────────┘  └───────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Demo Application: "PetClinic Lite"

A minimal microservices application with intentional failure points:

### Components

| Service | Description | Failure Scenarios |
|---------|-------------|-------------------|
| `demo-api` | REST API (Python/FastAPI) | CrashLoopBackOff, OOMKill, ImagePullBackOff |
| `demo-worker` | Background job processor | Deadlock, Resource exhaustion |
| `demo-db` | PostgreSQL database | Connection limits, Storage full |
| `demo-redis` | Cache layer | Memory pressure, Eviction issues |

### Pre-Built Failure Scenarios

1. **CrashLoopBackOff** - Missing required environment variable
2. **OOMKilled** - Memory leak simulation
3. **ImagePullBackOff** - Invalid image tag
4. **Pending Pod** - Insufficient resources
5. **Service Unreachable** - Misconfigured selector
6. **Liveness Probe Failure** - Endpoint returning 500
7. **Resource Quota Exceeded** - CPU/Memory limits hit

---

## Complete Workflow

### Step 1: Create Failure
```bash
# Apply a broken deployment
kubectl apply -f examples/incidents/crashloop-missing-env.yaml
```

### Step 2: AEGIS Detects & Analyzes
```bash
# K8sGPT scans cluster
k8sgpt analyze --filter=Pod --namespace=production --explain

# AEGIS CLI triggers full workflow
aegis analyze pod/demo-api --namespace production
```

### Step 3: RCA Generated
```
Root Cause: Pod demo-api is in CrashLoopBackOff state
Reasoning: Container 'api' exited with code 1. Missing required
           environment variable DATABASE_URL.
Severity: HIGH
Confidence: 0.95
```

### Step 4: Fix Proposed
```yaml
# Proposed fix
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-api-env
data:
  DATABASE_URL: "postgresql://demo-db:5432/app"
---
# Patch: Add envFrom to deployment
```

### Step 5: Shadow Verification
```bash
# AEGIS creates isolated vCluster
vcluster create shadow-001 --namespace aegis-shadows

# Clones production workload
# Applies proposed fix
# Runs verification tests
# Reports success/failure
```

### Step 6: Production Apply (if verified)
```bash
# Auto-apply fix to production
kubectl apply -f generated-fix.yaml --namespace production
```

---

## Installation Requirements

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Kind | 0.20+ | Local Kubernetes cluster |
| kubectl | 1.28+ | Kubernetes CLI |
| Helm | 3.12+ | Package manager |
| k8sgpt | 0.3+ | Kubernetes diagnostics |
| vcluster | 0.19+ | Shadow environments |
| Ollama | 0.1+ | Local LLM inference |

### Quick Install Commands

```bash
# Kind (Kubernetes in Docker)
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind

# K8sGPT
curl -LO https://github.com/k8sgpt-ai/k8sgpt/releases/latest/download/k8sgpt_Linux_x86_64.tar.gz
tar -xzf k8sgpt_Linux_x86_64.tar.gz && sudo mv k8sgpt /usr/local/bin/

# vCluster
curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
chmod +x vcluster && sudo mv vcluster /usr/local/bin/

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3:mini
```

---

## File Structure

```
examples/
├── cluster/
│   └── kind-config.yaml          # Kind cluster configuration
├── demo-app/
│   ├── namespace.yaml            # Production namespace
│   ├── demo-api.yaml             # API deployment + service
│   ├── demo-worker.yaml          # Worker deployment
│   ├── demo-db.yaml              # PostgreSQL statefulset
│   ├── demo-redis.yaml           # Redis deployment
│   └── kustomization.yaml        # Kustomize overlay
├── incidents/
│   ├── crashloop-missing-env.yaml
│   ├── oomkill-memory-leak.yaml
│   ├── imagepull-bad-tag.yaml
│   ├── pending-no-resources.yaml
│   ├── service-wrong-selector.yaml
│   └── liveness-failure.yaml
├── monitoring/
│   ├── prometheus-stack.yaml
│   └── grafana-dashboards/
└── shadow/
    └── vcluster-template.yaml
```

---

## Shadow Verification Deep Dive

### How It Works

1. **Create Shadow Cluster**
   ```bash
   vcluster create shadow-$INCIDENT_ID \
     --namespace aegis-shadows \
     --connect=false
   ```

2. **Clone Production State**
   ```bash
   # Export current deployment
   kubectl get deployment demo-api -n production -o yaml > /tmp/clone.yaml

   # Apply to shadow (via vcluster context)
   vcluster connect shadow-$INCIDENT_ID --namespace aegis-shadows
   kubectl apply -f /tmp/clone.yaml
   ```

3. **Apply Proposed Fix**
   ```bash
   kubectl apply -f proposed-fix.yaml
   ```

4. **Run Verification Tests**
   - Health check endpoints
   - Locust load testing
   - Security scans (Trivy, ZAP)
   - Custom assertions

5. **Collect Results**
   ```json
   {
     "shadow_id": "shadow-001",
     "verification_passed": true,
     "tests_run": 15,
     "tests_passed": 15,
     "duration_seconds": 45,
     "recommendation": "APPLY_TO_PRODUCTION"
   }
   ```

6. **Cleanup**
   ```bash
   vcluster delete shadow-$INCIDENT_ID --namespace aegis-shadows
   ```

---

## K8sGPT Configuration

### Setup with Ollama Backend

```bash
# Add Ollama as AI backend
k8sgpt auth add --backend ollama --baseurl http://localhost:11434 --model phi3:mini

# Set as default
k8sgpt auth default --backend ollama

# Verify
k8sgpt auth list
```

### Sample Analysis Output

```bash
$ k8sgpt analyze --filter=Pod --namespace=production --explain

0: Pod production/demo-api-7d9f8b6c5d-x2k4m
   - Error: CrashLoopBackOff

   Explanation: The container "api" in this pod is repeatedly crashing
   and being restarted by Kubernetes. The last termination reason was
   "Error" with exit code 1.

   Possible causes:
   1. Missing environment variables required by the application
   2. Configuration file not mounted correctly
   3. Database connection failing on startup

   Suggested actions:
   - Check container logs: kubectl logs demo-api-7d9f8b6c5d-x2k4m -n production
   - Verify environment variables are set correctly
   - Ensure dependent services (database, redis) are running
```

---

## Demo Script

```bash
#!/bin/bash
# Full AEGIS Demo Script

# 1. Setup cluster
make demo-cluster-create

# 2. Deploy healthy application
kubectl apply -k examples/demo-app/

# 3. Verify everything works
kubectl wait --for=condition=ready pod -l app=demo-api -n production --timeout=60s

# 4. Inject failure
kubectl apply -f examples/incidents/crashloop-missing-env.yaml

# 5. Watch AEGIS detect and fix
aegis analyze pod/demo-api --namespace production --auto-fix

# 6. Cleanup
make demo-cluster-delete
```

---

## Next Steps

1. Run `make demo-setup` to install all prerequisites
2. Run `make demo-cluster-create` to create Kind cluster
3. Run `make demo-app-deploy` to deploy demo application
4. Run `make demo-incident-inject` to create a failure scenario
5. Run `aegis analyze` to trigger the full workflow
