# K8sGPT Operator Integration for AEGIS

This directory contains the configuration and setup files for integrating the K8sGPT operator with AEGIS.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Kubernetes Cluster                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    watches    ┌─────────────┐                  │
│  │   K8sGPT    │──────────────▶│    Pods     │                  │
│  │  Operator   │               │ Deployments │                  │
│  └──────┬──────┘               │  Services   │                  │
│         │                      └─────────────┘                  │
│         │ creates                                                │
│         ▼                                                        │
│  ┌─────────────┐               ┌─────────────┐                  │
│  │   Result    │──────────────▶│    AEGIS    │                  │
│  │    CRDs     │   watches     │  Operator   │                  │
│  └─────────────┘               └──────┬──────┘                  │
│         │                             │                          │
│         │                             │ triggers                 │
│         │                             ▼                          │
│         │                      ┌─────────────┐                  │
│         │                      │    AEGIS    │                  │
│         │                      │  Workflow   │                  │
│         │                      │  (LangGraph)│                  │
│         │                      └──────┬──────┘                  │
│         │                             │                          │
│         │                             │ RCA + Solutions          │
│         │                             ▼                          │
│         │                      ┌─────────────┐                  │
│         └─────────────────────▶│   Ollama    │◀─────────────────│
│            AI Analysis         │  (LocalAI)  │                  │
│                                └─────────────┘                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `k8sgpt-values.yaml` | Helm values for K8sGPT operator installation |
| `k8sgpt-cr.yaml` | K8sGPT custom resource configuration |
| `k8sgpt_handler.py` | Kopf handler for watching K8sGPT Results |
| `README.md` | This documentation |

## Prerequisites

1. **Kubernetes Cluster**: minikube, kind, or any Kubernetes cluster
2. **Helm v3**: For installing K8sGPT operator
3. **Ollama**: Running locally or accessible from the cluster
4. **kubectl**: Configured with cluster access

## Quick Start

### 1. Start Ollama

```bash
# Start Ollama server
ollama serve

# In another terminal, pull the model
ollama pull llama3.2:latest
```

### 2. Start Minikube

```bash
# Start minikube with enough resources
minikube start --cpus=4 --memory=8192 --driver=docker

# Enable required addons
minikube addons enable metrics-server
minikube addons enable ingress
```

### 3. Install K8sGPT Operator

```bash
# Add Helm repository
helm repo add k8sgpt https://charts.k8sgpt.ai/
helm repo update

# Create namespace
kubectl create namespace k8sgpt-system

# Create secret for Ollama (dummy key for local Ollama)
kubectl create secret generic k8sgpt-secret \
  --from-literal=apikey=ollama-no-auth \
  -n k8sgpt-system

# Install operator
helm install k8sgpt-operator k8sgpt/k8sgpt-operator \
  -n k8sgpt-system \
  -f k8sgpt-values.yaml

# Wait for operator to be ready
kubectl wait --for=condition=available deployment/k8sgpt-operator \
  -n k8sgpt-system --timeout=120s
```

### 4. Apply K8sGPT Configuration

```bash
# Apply the K8sGPT CR
kubectl apply -f k8sgpt-cr.yaml

# Verify
kubectl get k8sgpt -n k8sgpt-system
```

### 5. Test the Integration

```bash
# Deploy a pod with a bad image tag
kubectl apply -f ../../examples/incidents/imagepull-bad-tag.yaml

# Wait for K8sGPT to analyze (30-60 seconds)
sleep 60

# Check for Results
kubectl get results.core.k8sgpt.ai -A

# View Result details
kubectl get results.core.k8sgpt.ai -A -o yaml
```

### 6. Start AEGIS Operator

```bash
# Integrate the handler into your operator
# Copy k8sgpt_handler.py to your handlers directory

# Run the operator
kopf run -m aegis.k8s_operator
```

## Handler Integration

To integrate the K8sGPT handler with your existing AEGIS operator:

### Option A: Copy the handler file

```bash
# Copy to your handlers directory
cp k8sgpt_handler.py /path/to/aegis/operators/handlers/

# Update handlers/__init__.py to import it
```

### Option B: Import directly

Add to your operator's main module:

```python
# In your operator's main.py or __init__.py
from deploy.k8sgpt.k8sgpt_handler import (
    handle_k8sgpt_result_create,
    handle_k8sgpt_result_update,
    handle_k8sgpt_result_delete,
)
```

### Option C: Run as separate operator

```bash
# Run K8sGPT handler as standalone Kopf operator
kopf run deploy/k8sgpt/k8sgpt_handler.py
```

## Configuration

### Ollama Connection

The K8sGPT operator needs to reach Ollama. Update `k8sgpt-values.yaml`:

```yaml
# For minikube (host access)
k8sgpt:
  baseUrl: http://host.minikube.internal:11434/v1

# For Ollama running in cluster
k8sgpt:
  baseUrl: http://ollama.ollama-system.svc:11434/v1

# For external Ollama
k8sgpt:
  baseUrl: http://your-ollama-host:11434/v1
```

### Analyzers

Configure which Kubernetes resources to analyze in `k8sgpt-cr.yaml`:

```yaml
spec:
  filters:
    - Pod           # Analyze Pod issues
    - Deployment    # Analyze Deployment issues
    - Service       # Analyze Service issues
    # Add or remove as needed
```

### AI Backend

K8sGPT supports multiple backends. For Ollama, use `localai`:

```yaml
spec:
  ai:
    backend: localai
    model: llama3.2:latest
    # Other options: openai, azureopenai, cohere, anthropic
```

## Troubleshooting

### K8sGPT operator not starting

```bash
# Check operator logs
kubectl logs -n k8sgpt-system deployment/k8sgpt-operator

# Check events
kubectl get events -n k8sgpt-system
```

### No Results being created

```bash
# Check K8sGPT CR status
kubectl describe k8sgpt -n k8sgpt-system k8sgpt-aegis

# Verify analyzers are running
kubectl get pods -n k8sgpt-system

# Check if there are actual issues to detect
kubectl get pods -A | grep -E 'Error|CrashLoop|ImagePull'
```

### Ollama connection issues

```bash
# From inside minikube, test Ollama connectivity
minikube ssh
curl http://host.minikube.internal:11434/api/tags

# Verify Ollama is serving
curl http://localhost:11434/api/tags
```

### AEGIS handler not triggering

```bash
# Check Kopf operator logs
kopf run -m aegis.k8s_operator --verbose

# Verify Result CRD exists
kubectl get crd results.core.k8sgpt.ai
```

## Result CRD Schema

K8sGPT creates Result CRDs with this structure:

```yaml
apiVersion: core.k8sgpt.ai/v1alpha1
kind: Result
metadata:
  name: <unique-name>
  namespace: k8sgpt-system
spec:
  backend: localai
  kind: Pod           # Resource type with issue
  name: my-pod        # Resource name
  error:              # List of detected errors
    - "Back-off pulling image..."
    - "ImagePullBackOff..."
  details: |          # AI-generated explanation
    The pod is failing because the image tag
    'python:3.99-nonexistent' does not exist...
  parentObject: ""    # Parent resource reference
```

## Next Steps

1. **Customize the handler**: Modify `k8sgpt_handler.py` to integrate with your AEGIS workflow
2. **Add more analyzers**: Enable additional K8sGPT analyzers for comprehensive coverage
3. **Set up notifications**: Configure K8sGPT sinks for Slack/webhook notifications
4. **Shadow verification**: Use AEGIS shadow environments to test fixes before applying

## Resources

- [K8sGPT Documentation](https://docs.k8sgpt.ai/)
- [K8sGPT Operator GitHub](https://github.com/k8sgpt-ai/k8sgpt-operator)
- [K8sGPT Helm Chart](https://artifacthub.io/packages/helm/k8sgpt/k8sgpt-operator)
- [Ollama Documentation](https://ollama.ai/)
- [Kopf Documentation](https://kopf.readthedocs.io/)
