# Skill: Kubernetes Diagnostics with k8sGPT Integration

## Metadata
- **Domain**: Kubernetes Troubleshooting, SRE, Observability
- **Tools**: k8sGPT, kubectl, prometheus, grafana
- **Complexity**: Advanced
- **Autonomy**: Read-Only (diagnostic only, no auto-remediation)

## Capability Statement
Expert in diagnosing Kubernetes cluster issues using k8sGPT-enhanced analysis. Provides structured Root Cause Analysis (RCA) with actionable remediation steps, optimized for autonomous SRE workflows.

## Core Competencies

### 1. Comprehensive Cluster Analysis
- Pod crash loops and OOMKills
- Network connectivity issues (CNI, NetworkPolicy)
- Resource exhaustion (CPU, memory, disk, PID)
- Configuration errors (ConfigMap, Secret mounts)
- RBAC permission denials
- StatefulSet and PVC issues
- Node health and taints
- Ingress/Service misconfiguration

### 2. k8sGPT Integration Patterns
```bash
# Structured analysis output for LangGraph agents
k8sGPT analyze --explain --backend ollama --output json
k8sGPT analyze --filter=Pod,Service --namespace production
k8sGPT analyze --with-doc --anonymize
```

### 3. Multi-Layer Diagnostic Protocol
```
Layer 1: Resource-Level (Pod, Service, Deployment)
Layer 2: Node-Level (kubelet, container runtime)
Layer 3: Control Plane (API server, scheduler, controller-manager)
Layer 4: Network (CNI, DNS, NetworkPolicies)
Layer 5: Storage (CSI, PVC, StorageClass)
```

## Execution Protocol

### Phase 1: Triage (60 seconds)
1. **Cluster Health Snapshot**
   ```bash
   kubectl get nodes -o wide
   kubectl top nodes
   kubectl get pods --all-namespaces | grep -v Running
   kubectl get events --sort-by='.lastTimestamp' | tail -20
   ```

2. **k8sGPT Quick Scan**
   ```bash
   k8sGPT analyze --explain --filter=Service,Ingress,Pod,PVC
   ```

3. **Initial Classification**
   - 🔴 P0: Cluster-wide outage, data loss risk
   - 🟠 P1: Service degradation, partial outage
   - 🟡 P2: Non-critical errors, warnings
   - 🟢 P3: Informational, optimization opportunities

### Phase 2: Deep Dive (5-10 minutes)
1. **Resource Inspection**
   ```bash
   # For failing pods
   kubectl describe pod <name> -n <namespace>
   kubectl logs <pod> --previous --tail=100
   kubectl get pod <pod> -o yaml | yq '.status'

   # For services
   kubectl get endpoints <service> -n <namespace>
   kubectl describe service <service> -n <namespace>
   ```

2. **Network Diagnostics**
   ```bash
   # DNS resolution
   kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- nslookup kubernetes.default

   # NetworkPolicy check
   kubectl get networkpolicy --all-namespaces
   kubectl describe networkpolicy <policy> -n <namespace>
   ```

3. **Node-Level Analysis**
   ```bash
   kubectl describe node <node-name>
   kubectl get --raw /api/v1/nodes/<node>/proxy/metrics/cadvisor
   ```

### Phase 3: Structured RCA Generation
Output format for LangGraph RCA agent:

```json
{
  "incident_id": "INC-2024-001",
  "severity": "P1",
  "affected_resources": [
    {"kind": "Pod", "name": "api-server-7f8d9", "namespace": "prod"}
  ],
  "symptoms": [
    "CrashLoopBackOff with exit code 137",
    "OOMKilled events in last 10 minutes"
  ],
  "root_cause": {
    "category": "Resource Exhaustion",
    "details": "Memory limit 256Mi exceeded, actual usage 512Mi",
    "evidence": [
      "kubectl top pod shows 98% memory usage",
      "OOMKilled event at 2024-01-24T10:15:23Z"
    ]
  },
  "contributing_factors": [
    "Recent traffic spike (3x normal load)",
    "Memory limit not updated after code changes"
  ],
  "impact_assessment": {
    "users_affected": "~5000",
    "duration": "15 minutes",
    "business_impact": "API latency +200ms"
  },
  "remediation_steps": [
    {
      "step": 1,
      "action": "Increase memory limit to 1Gi",
      "command": "kubectl patch deployment api-server -n prod --patch '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"api\",\"resources\":{\"limits\":{\"memory\":\"1Gi\"}}}]}}}}'",
      "risk": "low",
      "requires_approval": true
    },
    {
      "step": 2,
      "action": "Add HPA for auto-scaling",
      "command": "kubectl autoscale deployment api-server -n prod --cpu-percent=70 --min=3 --max=10",
      "risk": "medium",
      "requires_approval": true
    }
  ],
  "prevention": [
    "Implement resource quotas",
    "Add vertical pod autoscaler",
    "Set up Prometheus alerts for memory usage >80%"
  ]
}
```

## Integration with MCP Context7

### Auto-Fetch Documentation
Before diagnosing, query context7 for:
```python
# Via MCP server
context7.search("kubernetes pod crashloopbackoff troubleshooting")
context7.search("k8sGPT configuration best practices")
context7.search("kopf operator error handling patterns")
```

### Documentation Cross-Reference
Map k8sGPT findings to official docs:
- Pod errors → Kubernetes Pod Lifecycle docs
- Network issues → CNI plugin documentation
- Storage problems → CSI driver specs

## Common Failure Patterns

### Pattern 1: ImagePullBackOff
```yaml
Symptoms:
  - Event: Failed to pull image
  - Status: ImagePullBackOff or ErrImagePull

Root Causes:
  - Invalid image tag
  - Private registry auth missing
  - Network egress blocked
  - Rate limiting (Docker Hub)

Diagnostics:
  - Check imagePullSecrets in ServiceAccount
  - Test registry connectivity from node
  - Verify image exists: docker manifest inspect <image>

Remediation:
  - Add imagePullSecrets
  - Use local registry mirror
  - Update to valid tag
```

### Pattern 2: CrashLoopBackOff
```yaml
Symptoms:
  - Pod restarts continuously
  - Increasing backoff delay

Root Causes:
  - Application crash (exit code != 0)
  - Failed liveness probe
  - OOMKilled (exit code 137)
  - Configuration error

Diagnostics:
  - kubectl logs <pod> --previous
  - Check exit code in pod status
  - Review probe configuration
  - Inspect resource limits vs usage

Remediation:
  - Fix application bug
  - Adjust probe timings
  - Increase resource limits
  - Fix ConfigMap/Secret mounts
```

### Pattern 3: Service Unreachable
```yaml
Symptoms:
  - Endpoints empty
  - Connection refused/timeout

Root Causes:
  - Label selector mismatch
  - NetworkPolicy blocking
  - Pods not ready
  - DNS resolution failure

Diagnostics:
  - kubectl get endpoints <service>
  - Compare service selector to pod labels
  - Test pod-to-pod connectivity
  - Check NetworkPolicies

Remediation:
  - Fix label selectors
  - Update NetworkPolicy rules
  - Verify readiness probe
  - Restart CoreDNS if DNS issue
```

## k8sGPT Configuration for Autonomous SRE

### Backend Integration
```yaml
# ~/.k8sgpt/config.yaml (if using file-based config)
backend: ollama
model: llama3.1:70b
temperature: 0.1
max_tokens: 2000

filters:
  - Pod
  - Service
  - Deployment
  - StatefulSet
  - PersistentVolumeClaim
  - Ingress
  - Node

output_format: json
explain: true
anonymize: true  # Remove cluster-specific identifiers
with_doc: true   # Include K8s documentation links
```

### Integration with LangGraph Agents
```python
# Diagnostic Agent Node
async def k8sgpt_analyze(state: DiagnosticState):
    """Run k8sGPT analysis and parse results."""
    import subprocess
    import json

    result = subprocess.run(
        ['k8sGPT', 'analyze', '--explain', '--output', 'json'],
        capture_output=True,
        text=True
    )

    findings = json.loads(result.stdout)

    return {
        'findings': findings,
        'severity': classify_severity(findings),
        'affected_namespaces': extract_namespaces(findings)
    }
```

## Verification & Validation

### Post-Diagnostic Checklist
- [ ] All affected resources identified
- [ ] Root cause clearly articulated
- [ ] Evidence links to logs/metrics provided
- [ ] Remediation steps are actionable
- [ ] Risk assessment completed
- [ ] Prevention measures documented
- [ ] Findings validated against k8sGPT output

### Handoff to Remediation Agent
```json
{
  "diagnostic_complete": true,
  "rca_document": "rca-inc-001.json",
  "remediation_plan": "remediation-inc-001.json",
  "approval_required": true,
  "estimated_fix_time": "10 minutes",
  "rollback_plan": "rollback-inc-001.json"
}
```

## Output Artifacts
1. **RCA Report** (`rca-<incident-id>.json`) - Structured root cause analysis
2. **Remediation Plan** (`remediation-<incident-id>.json`) - Step-by-step fix
3. **Evidence Package** (`evidence-<incident-id>.tar.gz`) - Logs, manifests, metrics
4. **Timeline** (`timeline-<incident-id>.md`) - Incident chronology
5. **Post-Mortem Template** (`postmortem-<incident-id>.md`) - Blameless review

## Security & Privacy
- Always use `--anonymize` flag with k8sGPT
- Redact secrets/tokens from logs
- Do not expose cluster internals in RCA reports
- Sanitize PII before sending to LLM backends
- Use RBAC to limit diagnostic scope

## Performance Optimization
- Cache k8sGPT analysis results (5 min TTL)
- Parallelize resource inspection
- Use field selectors to reduce API calls
- Limit log retrieval to last 100 lines initially
- Implement circuit breakers for slow API calls
