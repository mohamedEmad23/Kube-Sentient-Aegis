# AEGIS Shadow Testing - Cluster Setup Commands

## Start Minikube Cluster

```bash
# Start minikube with sufficient resources for shadow testing
minikube start \
  --cpus=4 \
  --memory=8192 \
  --driver=docker \
  --kubernetes-version=v1.28.0

# Verify cluster is running
kubectl cluster-info
kubectl get nodes
```

## Install vCluster CLI

```bash
# Install vcluster CLI (if not already installed)
curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
chmod +x vcluster
sudo mv vcluster /usr/local/bin/

# Verify installation
vcluster --version
```

## Setup AEGIS Namespace

```bash
# Create AEGIS namespace
kubectl create namespace aegis-system

# Label namespace
kubectl label namespace aegis-system aegis.io/managed-by=aegis
```

## Deploy Demo Application

```bash
# Deploy a simple demo app for testing
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: demo-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-web
  namespace: demo-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-web
  template:
    metadata:
      labels:
        app: demo-web
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
          limits:
            cpu: 200m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: demo-web
  namespace: demo-app
spec:
  type: ClusterIP
  selector:
    app: demo-web
  ports:
  - port: 80
    targetPort: 80
EOF

# Wait for deployment to be ready
kubectl wait --for=condition=available --timeout=60s deployment/demo-web -n demo-app
```

## Verify Cluster Resources

```bash
# Check node resources
kubectl top nodes || echo "Metrics server not installed"

# Check available resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# List all pods
kubectl get pods -A
```

## Test AEGIS Shadow Manager (Python)

```bash
cd /home/mohammed-emad/VS-CODE/unifonic-hackathon

# Activate virtual environment
source .venv/bin/activate

# Run import tests
.venv/bin/python test_imports.py

# Run unit tests
.venv/bin/python -m pytest tests/integration/test_shadow_workflow.py -v

# Test shadow creation with real cluster
.venv/bin/python -c "
import asyncio
from aegis.shadow.manager import ShadowManager

async def main():
    manager = ShadowManager()
    print(f'Shadow Manager initialized')
    print(f'Runtime: {manager.runtime}')
    print(f'Max concurrent: {manager.max_concurrent}')

    # Check cluster resources
    resources = await manager._check_cluster_resources()
    print(f'Cluster resources:')
    print(f'  Sufficient: {resources[\"sufficient\"]}')
    print(f'  Available CPU: {resources[\"available_cpu\"]}')
    print(f'  Available Memory: {resources[\"available_memory\"]}')

    # List active shadows
    active = await manager.list_active_shadows()
    print(f'Active shadows: {len(active)}')

asyncio.run(main())
"
```

## Test Shadow Creation with Real Workload

```bash
# Create a shadow environment for the demo-web deployment
.venv/bin/python -c "
import asyncio
from aegis.shadow.manager import ShadowManager

async def main():
    manager = ShadowManager()

    try:
        print('Creating shadow environment...')
        shadow = await manager.create_shadow(
            source_namespace='demo-app',
            source_resource='demo-web',
            source_resource_kind='Deployment',
            shadow_id='demo-test-001'
        )

        print(f'✓ Shadow created successfully!')
        print(f'  ID: {shadow.id}')
        print(f'  Namespace: {shadow.namespace}')
        print(f'  Status: {shadow.status.value}')

        # List active shadows
        active = await manager.list_active_shadows()
        print(f'Active shadows: {len(active)}')

        # Cleanup
        print('Cleaning up shadow...')
        await manager.cleanup_shadow(shadow.id)
        print('✓ Cleanup complete')

    except Exception as e:
        print(f'✗ Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(main())
"
```

## Monitor Shadow Environments

```bash
# Watch shadow namespaces
kubectl get ns -l aegis.io/shadow=true --watch

# Check vCluster instances
kubectl get pods -A -l app=vcluster

# View shadow logs
kubectl logs -n aegis-system -l app=aegis-operator --tail=50
```

## Cleanup

```bash
# Delete all shadow environments
kubectl delete ns -l aegis.io/shadow=true

# Delete demo app
kubectl delete ns demo-app

# Stop minikube (if needed)
# minikube stop
```

## Troubleshooting

### vCluster Pods Pending

```bash
# Check events
kubectl get events --sort-by='.metadata.creationTimestamp' -A

# Check pod details
kubectl describe pod -n <shadow-namespace> <pod-name>

# Check resource availability
kubectl describe nodes
```

### Insufficient Resources

```bash
# Restart minikube with more resources
minikube delete
minikube start --cpus=6 --memory=12288 --driver=docker
```

### kubectl Context Issues

```bash
# List contexts
kubectl config get-contexts

# Switch context
kubectl config use-context minikube

# Verify connection
kubectl cluster-info
```
