# AEGIS Shadow Layer - Real World Testing Guide

## Prerequisites

```bash
# 1. Start Minikube with sufficient resources
minikube start --cpus=4 --memory=8192 --driver=docker

# 2. Verify cluster is running
kubectl cluster-info
kubectl get nodes

# 3. Install vCluster CLI
curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
chmod +x vcluster
sudo mv vcluster /usr/local/bin/
vcluster --version

# 4. Activate AEGIS virtual environment
cd /home/mohammed-emad/VS-CODE/unifonic-hackathon
source .venv/bin/activate

# 5. Start Ollama (required for AI analysis)
# In a separate terminal:
ollama serve
# Then pull the model:
ollama pull qwen2.5:14b
```

## Step 1: Deploy a Test Application with Issues

```bash
# Create a crashing pod (CrashLoopBackOff scenario)
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: test-app
---
apiVersion: v1
kind: Pod
metadata:
  name: crashloop-pod
  namespace: test-app
spec:
  containers:
  - name: app
    image: busybox:latest
    command: ["sh", "-c", "echo 'Starting...'; exit 1"]
  restartPolicy: Always
EOF

# Wait for it to enter CrashLoopBackOff
kubectl wait --for=condition=Ready --timeout=30s pod/crashloop-pod -n test-app || echo "Pod is crashing as expected"
kubectl get pod crashloop-pod -n test-app
```

## Step 2: Analyze with AEGIS CLI

```bash
# Run AEGIS analysis on the crashing pod
aegis analyze pod/crashloop-pod -n test-app

# This will:
# 1. Connect to K8sGPT (or use Ollama directly)
# 2. Analyze the pod issue
# 3. Generate RCA (Root Cause Analysis)
# 4. Propose a fix
# 5. Create a verification plan
```

## Step 3: Create Shadow Environment Manually

```bash
# Create a shadow environment for verification
aegis shadow create pod/crashloop-pod -n test-app --id test-shadow-001 --wait

# List shadow environments
aegis shadow list

# Check shadow status
aegis shadow status test-shadow-001
```

## Step 4: Full Analysis with Shadow Verification

```bash
# Run full analysis with automatic shadow verification
aegis analyze pod/crashloop-pod -n test-app --verify

# This will:
# 1. Analyze the issue
# 2. Generate a fix proposal
# 3. Create a shadow environment
# 4. Apply the fix in shadow
# 5. Verify the fix works
# 6. Prompt you to apply to production
```

## Step 5: Test with Deployment (More Realistic)

```bash
# Deploy a deployment with insufficient resources
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: prod-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-app
  namespace: prod-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25-alpine
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
  namespace: prod-app
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
EOF

# Wait for deployment
kubectl wait --for=condition=available --timeout=60s deployment/nginx-app -n prod-app

# Analyze the deployment
aegis analyze deployment/nginx-app -n prod-app
```

## Step 6: Test Shadow Creation Directly (Bypass Analysis)

```bash
# Create shadow from a healthy deployment
aegis shadow create deployment/nginx-app -n prod-app --id nginx-shadow-001 --wait

# Check the shadow namespace
kubectl get ns | grep aegis-shadow

# List pods in shadow namespace
kubectl get pods -n $(kubectl get ns | grep aegis-shadow-nginx | awk '{print $1}')

# Check vCluster pod
kubectl get pods -A | grep vcluster

# Get shadow kubeconfig and access shadow cluster
aegis shadow status nginx-shadow-001

# Cleanup shadow
aegis shadow delete nginx-shadow-001
```

## Step 7: Monitor Shadow Creation in Real-Time

```bash
# Terminal 1: Start shadow creation
aegis shadow create deployment/nginx-app -n prod-app --id realtime-test --wait

# Terminal 2: Watch namespaces
watch kubectl get ns -l aegis.io/shadow=true

# Terminal 3: Watch pods in aegis-shadow namespace
watch 'kubectl get pods -A | grep aegis-shadow'

# Terminal 4: Check vCluster resources
watch 'kubectl get statefulsets,services,pods -A | grep vcluster'
```

## Step 8: Test Resource Availability Check

```bash
# Run this Python script to test resource checking
.venv/bin/python -c "
import asyncio
from aegis.shadow.manager import ShadowManager

async def main():
    manager = ShadowManager()

    print('Checking cluster resources...')
    result = await manager._check_cluster_resources(
        required_cpu='500m',
        required_memory='1Gi'
    )

    print(f'Sufficient resources: {result[\"sufficient\"]}')
    print(f'Available CPU: {result[\"available_cpu\"]}')
    print(f'Available Memory: {result[\"available_memory\"]}')
    print(f'Requested CPU: {result[\"requested_cpu\"]}')
    print(f'Requested Memory: {result[\"requested_memory\"]}')

    if not result['sufficient']:
        print('WARNING: Cluster may not have enough resources!')

asyncio.run(main())
"
```

## Step 9: Test Complete Workflow End-to-End

```bash
# 1. Deploy problematic app
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: demo
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-api
  namespace: demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: demo-api
  template:
    metadata:
      labels:
        app: demo-api
    spec:
      containers:
      - name: api
        image: nginx:1.25-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
        livenessProbe:
          httpGet:
            path: /nonexistent
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
EOF

# 2. Wait for liveness probe to fail
sleep 30
kubectl get pods -n demo

# 3. Run full AEGIS analysis with shadow verification
aegis analyze deployment/demo-api -n demo --verify

# 4. Review the output:
#    - RCA should identify liveness probe failure
#    - Fix should suggest correcting the probe path
#    - Shadow verification should run automatically
#    - You'll be prompted to apply fix to production

# 5. If shadow passes, apply fix manually or with --auto-fix
aegis analyze deployment/demo-api -n demo --verify --auto-fix
```

## Step 10: Troubleshooting Commands

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check AEGIS logs (if running as operator)
kubectl logs -n aegis-system -l app=aegis-operator --tail=100

# Check shadow manager logs
grep -r "shadow" ~/.aegis/ 2>/dev/null || echo "No logs yet"

# List all shadow namespaces
kubectl get ns -l aegis.io/shadow=true

# Describe a stuck vCluster pod
SHADOW_NS=$(kubectl get ns -l aegis.io/shadow=true -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$SHADOW_NS" ]; then
  kubectl describe pods -n $SHADOW_NS
fi

# Check node resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# Force cleanup all shadows
kubectl delete ns -l aegis.io/shadow=true
```

## Expected Results

### Successful Shadow Creation

```
✓ Shadow environment nginx-shadow-001 created
  Namespace: aegis-shadow-nginx-shadow-001
  Status: ready
  Kubeconfig: /tmp/shadow-nginx-shadow-001.kubeconfig
```

### Successful Shadow Verification

```
[Shadow Verification]
Shadow ID: nginx-shadow-001
Result: PASSED

Apply this fix to the PRODUCTION cluster? [y/N]:
```

### Failed Shadow Creation (Resource Issues)

```
RuntimeError: vCluster resources not ready after 300s (StatefulSet: False, Service: True)

Diagnostics:
  StatefulSet: vcluster-nginx-shadow-001
    Status: 0/1 replicas ready
    Pods in namespace: 1
      Pod: vcluster-nginx-shadow-001-0
        Phase: Pending
        Conditions:
          - PodScheduled: False
        Events:
          - FailedScheduling: 0/1 nodes available: insufficient cpu
```

## Quick Sanity Check

```bash
# Run this one-liner to verify everything is set up correctly
(kubectl cluster-info && \
 ollama list | grep qwen && \
 aegis --version && \
 vcluster --version && \
 echo "✅ All prerequisites met!") || \
 echo "❌ Check prerequisites above"
```

## Common Issues

### Issue: "Ollama server is not available"
**Solution:**
```bash
# Start Ollama in background
ollama serve &
sleep 5
ollama pull qwen2.5:14b
```

### Issue: "vCluster resources not ready"
**Solution:**
```bash
# Check node resources
kubectl top nodes

# Increase minikube resources
minikube stop
minikube delete
minikube start --cpus=6 --memory=12288
```

### Issue: "Shadow verification skipped in mock mode"
**Solution:**
```bash
# Remove --mock flag
aegis analyze deployment/app -n namespace --verify
# NOT: aegis analyze deployment/app -n namespace --verify --mock
```

## Next Steps

Once shadow layer is working:
1. Test with K8sGPT integration
2. Test with actual incident CRDs
3. Test operator-based workflow
4. Enable security scanning in shadow
5. Add load testing to verification
