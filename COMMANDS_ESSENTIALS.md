# AEGIS Shadow Layer - Essential Commands

## Start the Cluster

```bash
# Start minikube with sufficient resources
minikube start --cpus=4 --memory=8192 --driver=docker

# Verify cluster is running
kubectl cluster-info
kubectl get nodes
```

## Deploy Test Application

```bash
# Create namespace and deploy nginx
kubectl create namespace demo-app
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: demo-app
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
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
EOF

# Wait for it
kubectl wait --for=condition=available --timeout=60s deployment/nginx -n demo-app
```

## Test AEGIS Commands

```bash
# Activate environment
cd /home/mohammed-emad/VS-CODE/unifonic-hackathon
source .venv/bin/activate

# Test 1: Analyze a deployment (requires Ollama running)
aegis analyze deployment/nginx -n demo-app

# Test 2: Create shadow environment manually
aegis shadow create deployment/nginx -n demo-app --wait

# Test 3: List shadow environments
aegis shadow list

# Test 4: Check shadow status
aegis shadow status <shadow-id-from-above>

# Test 5: Analyze with automatic shadow verification
aegis analyze deployment/nginx -n demo-app --verify

# Test 6: Delete shadow
aegis shadow delete <shadow-id>

# Test 7: Test with mock data (no cluster analysis needed)
aegis analyze deployment/test -n default --mock --verify
```

## Check Resources Before Creating Shadow

```bash
# Check cluster has resources
python -c "
import asyncio
from aegis.shadow.manager import ShadowManager

async def main():
    manager = ShadowManager()
    result = await manager._check_cluster_resources()
    print(f'Sufficient: {result[\"sufficient\"]}')
    print(f'CPU: {result[\"available_cpu\"]}')
    print(f'Memory: {result[\"available_memory\"]}')

asyncio.run(main())
"
```

## Monitor Shadow Creation

```bash
# Terminal 1: Create shadow
aegis shadow create deployment/nginx -n demo-app --id test-001 --wait

# Terminal 2: Watch resources
watch kubectl get ns,pods -A | grep -E '(aegis-shadow|vcluster)'

# Terminal 3: Check events
kubectl get events --all-namespaces --sort-by='.metadata.creationTimestamp' | tail -20
```

## Troubleshooting

```bash
# If cluster not starting
minikube delete
minikube start --cpus=4 --memory=8192

# If Ollama not running
ollama serve  # in separate terminal
ollama pull qwen2.5:14b

# Check AEGIS version
aegis --version

# Check imports work
python -c "from aegis.shadow.manager import ShadowManager; print('OK')"

# Force cleanup all shadows
kubectl delete ns -l aegis.io/shadow=true
```
