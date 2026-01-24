## Plan: AEGIS Shadow Layer & Observability Completion

Complete the shadow verification layer with enhanced verbosity, add a localhost dashboard with Prometheus/Grafana/Loki, and make agent output more explicit for hackathon demonstration.

---

### Current Shadow Layer Architecture (Clarification)

**What's Implemented:**
- **Namespace-based isolation** — Creates a `shadow-{id}` namespace, clones Deployment/Pod resources, applies fix patches, monitors health
- **NOT using vCluster/KataContainers** — The vCluster template exists at `examples/shadow/vcluster-template.yaml` but `ShadowManager` only creates namespaces

**How it works today:**
1. `create_shadow()` → Creates namespace `shadow-{uuid}`
2. `_clone_resource()` → Copies Deployment/Pod spec to shadow namespace
3. `_apply_changes()` → Patches the cloned resource with proposed fix
4. `_monitor_health()` → Polls pod status every 5s, calculates health score
5. `cleanup()` → Deletes shadow namespace

---

### Steps

1. **Enhance Agent Output Verbosity** — Add explicit step-by-step explanations in `src/aegis/agent/agents/` and `src/aegis/agent/prompts/` with structured reasoning chains, evidence citations, and demo-friendly formatting for examiners

2. **Create Grafana Dashboard + Loki Stack** — Add `loki`, `promtail` to `deploy/docker/docker-compose.yaml`, create AEGIS dashboard JSON at `deploy/docker/grafana/dashboards/`, provision datasources automatically

3. **Implement Shadow Verbose Logging** — Enhance `src/aegis/shadow/manager.py` to emit detailed step-by-step logs and structured events for each phase (clone, patch, verify, cleanup)

4. **Add Prometheus Alert Rules** — Create `deploy/docker/prometheus-alerts.yaml` with rules for pod failures, shadow verification failures, and agent errors

5. **Integrate Locust Load Testing (Optional)** — Add `load_test_config` execution in verifier agent when shadow verification runs (PoC: simple HTTP health check)

---

### Further Considerations

1. **vCluster Integration?** — Current namespace mode is sufficient for PoC demo. vCluster adds complexity (CLI dependency, 30s+ creation time). Recommend: Document as future work, keep namespace mode for demo.

2. **Real Cluster Testing?** — Options: (A) Kind cluster with demo-app — recommended for demo, (B) Minikube with custom app, (C) Remote K8s cluster. Demo script at `scripts/demo-setup.sh` supports Kind.

3. **K6 vs Locust?** — Locust is already in `VerificationPlan.load_test_config`. Implement simple Locust test runner for PoC; K6/Grafana K6 is more complex and should be future work.

---

## Detailed Implementation Breakdown

### ✅ IN-SCOPE (PoC Feasible)

| Item | Effort | Impact |
|------|--------|--------|
| Agent verbose output with reasoning chains | Medium | HIGH - Examiners can follow logic |
| Grafana dashboard for AEGIS metrics | Medium | HIGH - Visual proof of system working |
| Loki + Promtail for log aggregation | Low | MEDIUM - Log federation |
| Shadow layer verbose logging | Low | HIGH - Clear verification steps |
| Prometheus alerting rules | Low | MEDIUM - Production-ready feel |
| Demo script enhancement | Low | HIGH - One-command demo |

### ⏳ FUTURE WORK (Out of PoC Scope)

| Item | Complexity | Description |
|------|------------|-------------|
| **vCluster Runtime** | HIGH | Requires `vcluster` CLI, 30s+ spin-up, kubeconfig handling. Namespace mode is functionally equivalent for demo. |
| **KataContainers** | VERY HIGH | Requires specific hypervisor support, not available in Kind. Alternative: gVisor or standard containers. |
| **Grafana K6** | MEDIUM | Requires K6 binary, test script authoring, Prometheus remote write. Locust is simpler. |
| **OpenTelemetry Tracing** | MEDIUM | Settings exist but requires full instrumentation. Nice-to-have for production. |
| **StatefulSet/DaemonSet Cloning** | MEDIUM | Current implementation only handles Deployment/Pod. Extend `_clone_resource()`. |
| **Helm Chart Completion** | MEDIUM | Production deployment, but demo uses docker-compose. |

---

## Implementation Plan Details

### 1. Enhanced Agent Verbosity

**Goal:** Make agent output self-explanatory for non-technical examiners.

**Changes to prompt templates:**
- Add `## Step-by-Step Analysis` section requirement
- Require `## Evidence Summary` with bullet points
- Add `## Decision Rationale` explaining why this fix was chosen

**Changes to state models (`src/aegis/agent/state.py`):**
- Add `analysis_steps: list[str]` to `RCAResult`
- Add `evidence_summary: list[str]` to `RCAResult`
- Add `decision_rationale: str` to `FixProposal`

### 2. Grafana + Loki Dashboard Stack

**New files:**
```
deploy/docker/
├── loki-config.yaml           # Loki configuration
├── promtail-config.yaml       # Log collection config
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasources.yaml   # Prometheus + Loki
│   │   └── dashboards/
│   │       └── dashboards.yaml    # Dashboard provisioner
│   └── dashboards/
│       └── aegis-overview.json    # Main dashboard
```

**Dashboard Panels:**
- Incidents detected (by severity/namespace)
- Agent workflow success rate
- Shadow verification results
- LLM request latency
- Active shadow environments gauge

### 3. Shadow Layer Verbose Logging

**Add structured log events at each phase:**
```python
logger.info("shadow.clone.start", source_ns=source_ns, target_ns=shadow_ns)
logger.info("shadow.clone.complete", resource=resource_name, duration_ms=elapsed)
logger.info("shadow.patch.apply", patch_type=fix_type, changes=changes)
logger.info("shadow.verify.health_check", iteration=i, score=health_score)
logger.info("shadow.verify.complete", passed=passed, final_score=score)
```

### 4. Locust Load Testing (Simple PoC)

**Add to VerificationPlan execution:**
- If `load_test_config` is present, spawn simple HTTP requests
- For PoC: Use `httpx` async to hit pod's health endpoint
- Full Locust integration: Future work

---

## Testing Strategy

### Demo Workflow:
```bash
# 1. Start observability stack
docker-compose -f deploy/docker/docker-compose.yaml up -d

# 2. Create Kind cluster + deploy demo app
./scripts/demo-setup.sh

# 3. Inject incident
kubectl apply -f examples/incidents/crashloop-missing-env.yaml

# 4. Run AEGIS analysis
aegis analyze pod/demo-api --namespace production

# 5. View dashboard at http://localhost:3000 (Grafana)
# 6. View logs in Loki datasource
```

---

## File Changes Summary

### New Files to Create:
1. `deploy/docker/loki-config.yaml`
2. `deploy/docker/promtail-config.yaml`
3. `deploy/docker/grafana/provisioning/datasources/datasources.yaml`
4. `deploy/docker/grafana/provisioning/dashboards/dashboards.yaml`
5. `deploy/docker/grafana/dashboards/aegis-overview.json`
6. `deploy/docker/prometheus-alerts.yaml`

### Files to Modify:
1. `deploy/docker/docker-compose.yaml` — Add loki, promtail services + grafana provisioning volumes
2. `src/aegis/agent/state.py` — Add verbose fields to RCAResult, FixProposal
3. `src/aegis/agent/prompts/rca_prompts.py` — Add step-by-step analysis requirements
4. `src/aegis/agent/prompts/solution_prompts.py` — Add decision rationale requirements
5. `src/aegis/agent/prompts/verifier_prompts.py` — Add explicit verification steps
6. `src/aegis/shadow/manager.py` — Add verbose structured logging at each phase
7. `src/aegis/agent/agents/rca_agent.py` — Handle new verbose fields
8. `src/aegis/agent/agents/solution_agent.py` — Handle new verbose fields
9. `deploy/docker/prometheus.yaml` — Include alerting rules

---

## Future Work Documentation

### vCluster Implementation (Future)

When implementing full vCluster support:

```python
# In ShadowManager.create_shadow()
if self.settings.runtime == "vcluster":
    # 1. Create vCluster
    await self._run_command([
        "vcluster", "create", shadow_id,
        "--namespace", "aegis-shadows",
        "--connect=false",
        "--values", "/path/to/vcluster-template.yaml"
    ])

    # 2. Get kubeconfig
    kubeconfig = await self._run_command([
        "vcluster", "connect", shadow_id,
        "--namespace", "aegis-shadows",
        "--print"
    ])

    # 3. Use kubeconfig for all subsequent operations
    # 4. Cleanup: vcluster delete shadow_id
```

### KataContainers Implementation (Future)

Requirements:
- Hypervisor support (KVM/QEMU)
- KataContainers runtime installed
- RuntimeClass configuration in cluster
- Pod annotation: `runtimeClassName: kata`

Not feasible for Kind clusters; requires bare-metal or nested virtualization.

### Grafana K6 Integration (Future)

```yaml
# docker-compose addition
k6:
  image: grafana/k6:latest
  volumes:
    - ./k6-scripts:/scripts
  command: run /scripts/load-test.js
  environment:
    - K6_PROMETHEUS_RW_SERVER_URL=http://prometheus:9090/api/v1/write
```

Test script would verify:
- Response times under load
- Error rates
- Throughput capacity
