# AEGIS Technology Catalog - Quick Reference

## 📦 Complete Tools Inventory

### AI/LLM Integration

| Tool | Repository | License | Stars | Latest Version | Purpose |
|------|-----------|---------|-------|----------------|---------|
| **Ollama** | [ollama/ollama](https://github.com/ollama/ollama) | MIT | 157k | v0.13.2 | Local LLM inference server with GPU support |
| **vLLM** | [vllm-project/vllm](https://github.com/vllm-project/vllm) | Apache 2.0 | 65k | v0.12.0 | High-throughput production LLM serving |
| **K8sGPT** | [k8sgpt-ai/k8sgpt](https://github.com/k8sgpt-ai/k8sgpt) | Apache 2.0 | 7.2k | v0.4.26 | Kubernetes diagnostics with AI analysis |
| **LangGraph** | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | MIT | 22k | latest | Stateful agent orchestration framework |

### Kubernetes Sandboxing

| Tool | Repository | License | Stars | Latest Version | Purpose |
|------|-----------|---------|-------|----------------|---------|
| **vCluster** | [loft-sh/vcluster](https://github.com/loft-sh/vcluster) | Apache 2.0 | 10.7k | v0.30.3 | Virtual Kubernetes clusters in namespaces |
| **Kata Containers** | [kata-containers/kata-containers](https://github.com/kata-containers/kata-containers) | Apache 2.0 | 7.1k | v3.23.0 | VM-based container isolation |
| **gVisor** | [google/gvisor](https://github.com/google/gvisor) | Apache 2.0 | 17.3k | latest | Application kernel for container security |

### Observability Stack

| Tool | Repository | License | Stars | Latest Version | Purpose |
|------|-----------|---------|-------|----------------|---------|
| **Prometheus** | [prometheus/prometheus](https://github.com/prometheus/prometheus) | Apache 2.0 | 61.7k | v3.8.0 | Metrics collection and alerting (CNCF Graduated) |
| **Grafana Loki** | [grafana/loki](https://github.com/grafana/loki) | AGPL-3.0 | 27.1k | v3.6.2 | Horizontally scalable log aggregation |
| **OpenTelemetry Python** | [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python) | Apache 2.0 | 2.2k | v1.39 | Distributed tracing instrumentation |

### Security Tools

| Tool | Repository | License | Stars | Latest Version | Purpose |
|------|-----------|---------|-------|----------------|---------|
| **Falco** | [falcosecurity/falco](https://github.com/falcosecurity/falco) | Apache 2.0 | 8.5k | v0.42.1 | Runtime security monitoring (CNCF Graduated) |
| **Trivy** | [aquasecurity/trivy](https://github.com/aquasecurity/trivy) | Apache 2.0 | 30.4k | v0.68.1 | Comprehensive vulnerability scanner |
| **OWASP ZAP** | [zaproxy/zaproxy](https://github.com/zaproxy/zaproxy) | Apache 2.0 | 14.5k | v2.16.1 | Dynamic application security testing |

### Load Testing

| Tool | Repository | License | Stars | Latest Version | Purpose |
|------|-----------|---------|-------|----------------|---------|
| **Locust** | [locustio/locust](https://github.com/locustio/locust) | MIT | 27.2k | v2.42.6 | Python-based distributed load testing |
| **Grafana k6** | [grafana/k6](https://github.com/grafana/k6) | AGPL-3.0 | 29.4k | v1.4.2 | JavaScript load testing with Go core |

### Kubernetes Development

| Tool | Repository | License | Stars | Latest Version | Purpose |
|------|-----------|---------|-------|----------------|---------|
| **Kopf** | [nolar/kopf](https://github.com/nolar/kopf) | MIT | 2.5k | v1.39.0 | Pythonic Kubernetes operator framework |

### Cloud Infrastructure

| Tool | Repository | License | Stars | Latest Version | Purpose |
|------|-----------|---------|-------|----------------|---------|
| **Ubicloud** | [ubicloud/ubicloud](https://github.com/ubicloud/ubicloud) | AGPL-3.0 | 11.6k | latest | Open source AWS alternative |

---

## 🔧 Installation Commands

### Core Tools

```bash
# Ollama - Local LLM
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# vCluster - Virtual Kubernetes
curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
chmod +x vcluster && sudo mv vcluster /usr/local/bin

# K8sGPT - AI diagnostics
# macOS
brew install k8sgpt
# Linux (download binary)
curl -LO https://github.com/k8sgpt-ai/k8sgpt/releases/latest/download/k8sgpt_Linux_x86_64.tar.gz

# Trivy - Vulnerability Scanner
# macOS
brew install trivy
# Linux
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Falco - Runtime Security
# Add Falco helm repo
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco --namespace falco --create-namespace
```

### Python Dependencies

```bash
# Create virtual environment
python -m venv aegis-venv
source aegis-venv/bin/activate

# Install core packages
pip install \
  kopf==1.39.0 \
  kubernetes==31.0.0 \
  langgraph==0.3.0 \
  langchain-community==0.3.0 \
  prometheus-client==0.21.0 \
  opentelemetry-api==1.39.0 \
  opentelemetry-sdk==1.39.0 \
  locust==2.42.6 \
  httpx==0.28.0 \
  pydantic==2.10.0
```

### Helm Charts

```bash
# Prometheus + Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace

# Loki
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack --namespace logging --create-namespace

# vCluster
helm repo add loft https://charts.loft.sh
# Individual vclusters created via CLI
```

---

## 🖥️ GPU/LLM Configuration

### Model Memory Requirements (Ollama)

| Model | Parameters | VRAM Required | Best For |
|-------|------------|---------------|----------|
| `llama3.1:8b` | 8B | 8-10GB | General reasoning, code |
| `llama3.1:8b-q4_K_M` | 8B (quantized) | 5-6GB | Memory-constrained |
| `codellama:13b` | 13B | 14-16GB | Code generation |
| `mistral:7b` | 7B | 8GB | Fast inference |
| `deepseek-coder:6.7b` | 6.7B | 6-8GB | Code analysis |
| `qwen2.5:7b` | 7B | 8GB | Multilingual, code |

### Multi-GPU Configuration

```bash
# Set visible GPUs
export CUDA_VISIBLE_DEVICES=0,1,2

# Start Ollama with specific GPU
CUDA_VISIBLE_DEVICES=0 ollama serve

# vLLM tensor parallel across GPUs
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.9
```

### Ollama Configuration

```yaml
# ~/.ollama/config.yaml (example)
models:
  - name: llama3.1:8b
    options:
      num_gpu: 1
      num_ctx: 4096
      temperature: 0.7
      
server:
  host: 0.0.0.0
  port: 11434
```

---

## 📊 API Quick Reference

### Ollama API

```python
import httpx

# Generate completion
response = httpx.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.1:8b",
        "prompt": "Analyze this Kubernetes error...",
        "stream": False
    }
)
print(response.json()["response"])

# Chat completion
response = httpx.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "llama3.1:8b",
        "messages": [
            {"role": "system", "content": "You are a Kubernetes SRE expert."},
            {"role": "user", "content": "Pod crash with OOMKilled, what should I check?"}
        ]
    }
)
```

### K8sGPT Integration

```python
import subprocess
import json

def analyze_with_k8sgpt():
    result = subprocess.run(
        ["k8sgpt", "analyze", "--explain", "--output", "json", "--backend", "ollama"],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)
```

### vCluster Operations

```python
import subprocess

class VClusterManager:
    def create(self, name: str, namespace: str = "shadows"):
        subprocess.run([
            "vcluster", "create", name,
            "--namespace", namespace,
            "--connect=false"
        ])
        
    def get_kubeconfig(self, name: str, namespace: str = "shadows") -> str:
        result = subprocess.run([
            "vcluster", "connect", name,
            "--namespace", namespace,
            "--print"
        ], capture_output=True, text=True)
        return result.stdout
        
    def delete(self, name: str, namespace: str = "shadows"):
        subprocess.run([
            "vcluster", "delete", name,
            "--namespace", namespace
        ])
```

### Locust Load Test

```python
# locustfile.py
from locust import HttpUser, task, between

class ShadowVerificationUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def health_check(self):
        self.client.get("/health")
    
    @task(1)
    def api_endpoint(self):
        self.client.post("/api/v1/resource", json={"key": "value"})
```

---

## 🔐 Security Scanning Commands

### Trivy

```bash
# Scan container image
trivy image nginx:latest

# Scan Kubernetes cluster
trivy k8s --report summary cluster

# Scan with specific severity
trivy image --severity HIGH,CRITICAL myapp:latest

# Output as JSON
trivy image --format json -o results.json myapp:latest
```

### OWASP ZAP

```bash
# Quick scan
docker run -t zaproxy/zap-stable zap-baseline.py -t https://target.com

# API scan
docker run -t zaproxy/zap-stable zap-api-scan.py -t https://target.com/openapi.json -f openapi

# Full scan
docker run -t zaproxy/zap-stable zap-full-scan.py -t https://target.com
```

### Falco Rules

```yaml
# Custom Falco rule for Aegis
- rule: Aegis Shadow Environment Access
  desc: Detect unauthorized access to shadow environments
  condition: >
    container and
    container.name startswith "vcluster-" and
    evt.type in (execve, ptrace)
  output: >
    Shadow environment accessed
    (user=%user.name container=%container.name command=%proc.cmdline)
  priority: WARNING
  tags: [aegis, shadow, security]
```

---

## 📁 Project Structure

```
aegis/
├── operator/
│   ├── __init__.py
│   ├── main.py              # Kopf operator entry point
│   ├── handlers/
│   │   ├── incident.py      # Incident CRD handlers
│   │   └── shadow.py        # Shadow environment handlers
│   └── crds/
│       └── incident.yaml    # CustomResourceDefinition
├── agent/
│   ├── __init__.py
│   ├── graph.py             # LangGraph workflow
│   ├── llm.py               # Ollama integration
│   └── analyzer.py          # K8sGPT wrapper
├── shadow/
│   ├── __init__.py
│   ├── vcluster.py          # vCluster management
│   └── verification.py      # Test execution
├── security/
│   ├── __init__.py
│   ├── trivy.py             # Vulnerability scanning
│   └── zap.py               # DAST automation
├── observability/
│   ├── __init__.py
│   ├── metrics.py           # Prometheus integration
│   └── tracing.py           # OpenTelemetry setup
├── tests/
│   ├── unit/
│   └── integration/
├── deploy/
│   ├── helm/
│   │   └── aegis/
│   └── manifests/
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🔗 External Resources

### Documentation Links

| Tool | Documentation |
|------|---------------|
| Ollama | https://ollama.com/library |
| vCluster | https://www.vcluster.com/docs |
| K8sGPT | https://docs.k8sgpt.ai |
| LangGraph | https://langchain-ai.github.io/langgraph |
| Prometheus | https://prometheus.io/docs |
| Loki | https://grafana.com/docs/loki |
| Falco | https://falco.org/docs |
| Trivy | https://aquasecurity.github.io/trivy |
| OWASP ZAP | https://www.zaproxy.org/docs |
| Kata Containers | https://katacontainers.io/docs |
| gVisor | https://gvisor.dev/docs |
| Kopf | https://kopf.readthedocs.io |

### Community Resources

| Resource | URL |
|----------|-----|
| CNCF Landscape | https://landscape.cncf.io |
| Kubernetes Slack | https://kubernetes.slack.com |
| LangChain Discord | https://discord.gg/langchain |
| Ollama Discord | https://discord.gg/ollama |
