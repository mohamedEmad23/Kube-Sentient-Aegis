# 🛡️ AEGIS Project Overview & System Workflow

**Comprehensive Guide for Security Engineers**

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Complete Workflow Deep-Dive](#complete-workflow-deep-dive)
4. [Security Engineer Focus Areas](#security-engineer-focus-areas)
5. [Key Components Explained](#key-components-explained)
6. [Security Integration Points](#security-integration-points)

---

## 1. Project Overview {#project-overview}

### What is AEGIS?

**AEGIS (Autonomous SRE Agent with Shadow Verification)** is an AI-powered Kubernetes operator that autonomously detects, analyzes, and remediates production incidents using a revolutionary **shadow verification** approach.

### Core Innovation: Shadow Verification

Unlike traditional incident response systems that apply fixes directly to production, AEGIS:

1. **Detects** incidents automatically (Pod crashes, deployment failures, etc.)
2. **Analyzes** root causes using AI (K8sGPT + LLM agents)
3. **Proposes** fixes using AI reasoning
4. **Tests** fixes in isolated shadow environments **BEFORE** production
5. **Verifies** security, performance, and functionality
6. **Deploys** only after passing all verification tests

### Why This Matters

**Traditional Approach:**
```
Incident → Manual Analysis → Fix → Deploy to Production → Hope it works
                                                          ↓
                                                    (Often breaks more)
```

**AEGIS Approach:**
```
Incident → AI Analysis → Proposed Fix → Shadow Environment Testing →
Security Scan → Load Test → Human Approval → Deploy to Production
                                                          ↓
                                                    (Verified safe)
```

### Key Benefits

- ✅ **Zero production risk** - All fixes tested in isolated sandboxes
- ✅ **Automated security scanning** - Trivy, ZAP, Falco integrated
- ✅ **AI-powered analysis** - Faster root cause identification
- ✅ **Exploit verification** - Proof-of-concept generation in gVisor
- ✅ **Performance validation** - Load testing before deployment

---

## 2. System Architecture {#system-architecture}

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AEGIS OPERATOR (Kopf Framework)              │  │
│  │  • Monitors Pods/Deployments with aegis.io/monitor=true   │  │
│  │  • Detects incidents (CrashLoopBackOff, OOMKilled, etc.) │  │
│  │  • Triggers AI analysis workflow                           │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │         LANGGRAPH AGENT WORKFLOW                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │
│  │  │  RCA Agent   │→ │Solution Agent│→ │Verifier Agent│ │  │
│  │  │ (Root Cause) │  │  (Fix Gen)    │  │  (Testing)   │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │              SHADOW VERIFICATION LAYER                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │   vCluster   │  │     Kata     │  │    gVisor    │   │  │
│  │  │  (Isolation) │  │  (VM-based)  │  │  (Sandbox)   │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │              SECURITY & VERIFICATION                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │    Trivy     │  │  OWASP ZAP   │  │    Falco     │   │  │
│  │  │ (Vuln Scan)  │  │   (DAST)     │  │  (Runtime)   │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              OBSERVABILITY STACK                          │  │
│  │  Prometheus (Metrics) | Loki (Logs) | OpenTelemetry (Traces)│  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Operator** | Kopf (Python) | Kubernetes operator framework |
| **AI Agents** | LangGraph + Ollama | Multi-agent workflow orchestration |
| **K8s Analysis** | K8sGPT | Kubernetes diagnostics with AI |
| **Shadow Runtime** | vCluster | Virtual Kubernetes clusters |
| **Security Isolation** | Kata Containers | VM-based container isolation |
| **Exploit Sandbox** | gVisor | Application kernel sandboxing |
| **Vulnerability Scanner** | Trivy | Container/K8s scanning |
| **DAST Scanner** | OWASP ZAP | Dynamic application security testing |
| **Runtime Security** | Falco | Syscall monitoring |
| **Load Testing** | Locust/k6 | Performance validation |

---

## 3. Complete Workflow Deep-Dive {#complete-workflow-deep-dive}

### 3.1 Incident Detection Phase

**Location:** `src/aegis/k8s_operator/handlers/incident.py`

**How it works:**

1. **Pod Monitoring:**
   - Operator watches Pods with annotation `aegis.io/monitor: "enabled"`
   - Detects phase changes: `Failed`, `CrashLoopBackOff`, `ImagePullBackOff`, `OOMKilled`
   - Triggers analysis when unhealthy states detected

2. **Deployment Monitoring:**
   - Monitors `status.unavailableReplicas` field
   - Triggers incident if >50% replicas unavailable
   - Tracks rollout failures

**Code Flow:**
```python
@kopf.on.field("pods", field="status.phase")
async def handle_pod_phase_change(...):
    if new_phase in ["Failed", "CrashLoopBackOff"]:
        # Trigger AEGIS analysis
        await _analyze_pod_incident(resource_name, namespace, phase)
```

### 3.2 AI Analysis Phase

**Location:** `src/aegis/agent/graph.py`

**Workflow Steps:**

#### Step 1: K8sGPT Analysis
- Calls K8sGPT to analyze Kubernetes resources
- Gets structured diagnostics (problems, errors, recommendations)
- Provides context to LLM agents

#### Step 2: RCA Agent (Root Cause Analysis)
- **Input:** K8sGPT analysis + pod/deployment state
- **Process:** LLM analyzes logs, events, resource status
- **Output:** Root cause identification with confidence score
- **Routing:** If confidence < 0.7 → END (insufficient data)

#### Step 3: Solution Agent
- **Input:** RCA result + K8sGPT recommendations
- **Process:** LLM generates fix proposal (YAML patches, config changes)
- **Output:** Fix proposal with commands, confidence, risk level
- **Routing:** 
  - Low-risk fixes → END (apply directly)
  - High-risk fixes → Verifier Agent

#### Step 4: Verifier Agent
- **Input:** Fix proposal + original incident
- **Process:** Creates verification plan (security scans, load tests)
- **Output:** Verification plan with test specifications

**Code Flow:**
```python
# Workflow: START → rca_agent → solution_agent → verifier_agent → END
workflow = StateGraph(IncidentState)
workflow.add_node("rca_agent", rca_agent)
workflow.add_node("solution_agent", solution_agent)
workflow.add_node("verifier_agent", verifier_agent)
```

### 3.3 Shadow Verification Phase

**Location:** `src/aegis/shadow/manager.py` + `src/aegis/k8s_operator/handlers/shadow.py`

**Detailed Steps:**

#### Step 1: Create Shadow Environment
```python
shadow_env = await shadow_manager.create_shadow(
    source_namespace="production",
    source_resource="nginx-deployment",
    source_resource_kind="Deployment"
)
```

**What happens:**
- Creates isolated namespace: `aegis-shadow-{timestamp}`
- Clones production deployment to shadow namespace
- Applies resource quotas and network policies
- Configures observability (Prometheus scraping)

#### Step 2: Apply Proposed Fix
```python
changes = {
    "image": "nginx:1.25.1",  # Updated image
    "replicas": 3,            # Scale adjustment
    "env": {"DEBUG": "false"}  # Config change
}
await shadow_manager.run_verification(shadow_id, changes)
```

**What happens:**
- Patches deployment in shadow environment
- Waits for rollout to complete
- Monitors pod health

#### Step 3: Security Scanning (YOUR MAIN TASK)

**Current State:** Not yet implemented (empty `src/aegis/security/`)

**What needs to happen:**

1. **Trivy Scan:**
   ```python
   # In src/aegis/security/trivy.py (TO BE CREATED)
   scanner = TrivyScanner()
   result = await scanner.scan_image("nginx:1.25.1")
   if result["severity_counts"]["CRITICAL"] > 0:
       return False  # Block deployment
   ```

2. **OWASP ZAP Scan:**
   ```python
   # In src/aegis/security/zap.py (TO BE CREATED)
   zap = ZAPScanner()
   result = await zap.baseline_scan("http://shadow-service:8080")
   if result["risk_counts"]["High"] > 0:
       return False  # Block deployment
   ```

3. **Falco Monitoring:**
   - Custom rules detect suspicious activity in shadow
   - Alerts on unauthorized access, file modifications
   - Runtime behavior analysis

#### Step 4: Load Testing
- Locust/k6 generates traffic to shadow environment
- Measures response times, error rates
- Validates performance under load

#### Step 5: Health Monitoring
```python
health_score = await shadow_manager._monitor_health(env, duration=600)
# Returns 0.0-1.0 score based on:
# - Pod readiness
# - Container health
# - Resource utilization
```

**Pass Criteria:**
- Health score ≥ 0.8 (80%)
- No CRITICAL vulnerabilities
- No HIGH security risks
- Load test passed
- Performance within acceptable range

#### Step 6: Decision & Cleanup
```python
if passed:
    # Apply fix to production
    await apply_fix_to_production(fix_proposal)
else:
    # Reject fix, generate new proposal
    await refine_fix_proposal(original_incident)
    
# Always cleanup shadow
await shadow_manager.cleanup(shadow_id)
```

### 3.4 Production Deployment Phase

**If verification passes:**
- Fix is applied to production deployment
- Operator monitors rollout
- Metrics updated (incidents resolved, fixes applied)

**If verification fails:**
- Fix is rejected
- Incident remains open
- Solution Agent generates alternative fix
- Process repeats

---

## 4. Security Engineer Focus Areas {#security-engineer-focus-areas}

### 4.1 Your Primary Responsibilities

Based on `docs/SECURITY_ENGINEER_GUIDE.md`, you own:

#### Phase 1: Foundation (Days 3-4, 7-8)
- ✅ Kubernetes cluster security hardening
- ✅ vCluster security configuration
- ✅ Network policies for shadow environments

#### Phase 2: Core Security (Days 20-25)
- ✅ Shadow environment isolation (vCluster + Kata Containers)
- ✅ Verification test framework (Locust + ZAP integration)

#### Phase 3: Security Integration (Days 26-35) ⭐ **YOUR MAIN PHASE**
- ✅ **Falco runtime rules** (Days 26-28)
- ✅ **Trivy scanning pipeline** (Days 29-31)
- ✅ **OWASP ZAP automation** (Days 32-34)
- ✅ **gVisor sandboxing for exploits** (Day 35)

#### Phase 4: Security Scenarios (Days 39-43)
- ✅ **Scenario 2: SQL Injection** - WAF virtual patching + ZAP verification
- ✅ **Scenario 3: Insecure JWT** - Custom exploit generation

### 4.2 Critical Security Files to Create

#### 1. Trivy Scanner (`src/aegis/security/trivy.py`)
**Purpose:** Scan container images and Kubernetes resources for vulnerabilities

**Key Functions:**
```python
class TrivyScanner:
    async def scan_image(self, image: str) -> dict:
        """Scan container image for vulnerabilities."""
        # Returns: {"vulnerabilities": [...], "severity_counts": {...}, "passed": bool}
        
    async def scan_cluster(self, namespace: str) -> dict:
        """Scan Kubernetes cluster resources."""
        
    def parse_results(self, json_output: str) -> dict:
        """Parse Trivy JSON output."""
```

**Integration Point:** Called in `shadow/manager.py` during `run_verification()`

#### 2. OWASP ZAP Scanner (`src/aegis/security/zap.py`)
**Purpose:** Dynamic application security testing (DAST)

**Key Functions:**
```python
class ZAPScanner:
    async def baseline_scan(self, target_url: str) -> dict:
        """Quick security scan of target URL."""
        # Returns: {"alerts": [...], "risk_counts": {...}, "passed": bool}
        
    async def api_scan(self, openapi_spec: str) -> dict:
        """API-focused security scan."""
```

**Integration Point:** Called after fix deployment in shadow environment

#### 3. Falco Rules (`deploy/falco/aegis-rules.yaml`)
**Purpose:** Custom runtime security rules for shadow environments

**Key Rules:**
```yaml
- rule: AEGIS Shadow Environment Access
  desc: Detect unauthorized access to shadow environments
  condition: >
    k8s.ns.name startswith "aegis-shadow" and
    evt.type in (open, openat) and
    not user.name in (aegis-operator, system:serviceaccount:aegis-system)
  output: >
    Unauthorized access to shadow environment
    (user=%user.name container=%container.name)
  priority: WARNING
```

#### 4. Exploit Sandbox (`src/aegis/security/exploit/sandbox.py`)
**Purpose:** Safely execute LLM-generated exploit code

**Key Functions:**
```python
class ExploitSandbox:
    async def execute_exploit(
        self,
        exploit_code: str,
        target_url: str,
        timeout: int = 30
    ) -> dict:
        """Execute exploit in gVisor sandbox."""
        # Returns: {"exploitable": bool, "proof_of_concept": str, "evidence": [...]}
```

**Use Case:** When AEGIS detects insecure JWT, generate and test exploit PoC

### 4.3 Security Integration Workflow

```
┌─────────────────────────────────────────────────────────┐
│         SHADOW VERIFICATION SECURITY WORKFLOW           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Shadow Environment Created                          │
│     │                                                   │
│     ▼                                                   │
│  2. Deploy Proposed Fix                                 │
│     │                                                   │
│     ▼                                                   │
│  3. SECURITY SCANNING (YOUR CODE)                       │
│     ├─ Trivy: Scan container images                    │
│     │  └─ Block if CRITICAL/HIGH vulnerabilities        │
│     │                                                   │
│     ├─ ZAP: Scan API endpoints                         │
│     │  └─ Block if HIGH/MEDIUM security risks          │
│     │                                                   │
│     └─ Falco: Monitor runtime behavior                 │
│        └─ Alert on suspicious activity                  │
│     │                                                   │
│     ▼                                                   │
│  4. Load Testing (Locust)                              │
│     │                                                   │
│     ▼                                                   │
│  5. Security Report Generation                         │
│     ├─ Vulnerabilities found?                          │
│     ├─ Security tests passed?                         │
│     └─ Performance acceptable?                         │
│     │                                                   │
│     ▼                                                   │
│  6. Decision                                            │
│     ├─ PASS → Deploy to production                     │
│     └─ FAIL → Reject, generate new fix                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.4 Security Configuration

**Location:** `src/aegis/config/settings.py` (already has `SecuritySettings`)

**Current Settings:**
```python
class SecuritySettings(BaseSettings):
    trivy_enabled: bool = True
    zap_enabled: bool = True
    falco_enabled: bool = True
    gvisor_enabled: bool = True
    # ... more settings
```

**Environment Variables:**
```bash
SECURITY_TRIVY_ENABLED=true
SECURITY_TRIVY_SEVERITY=HIGH,CRITICAL
SECURITY_ZAP_ENABLED=true
SECURITY_ZAP_API_URL=http://localhost:8080
SECURITY_FALCO_ENABLED=true
```

---

## 5. Key Components Explained {#key-components-explained}

### 5.1 Operator (`src/aegis/k8s_operator/main.py`)

**Technology:** Kopf (Python Kubernetes operator framework)

**Responsibilities:**
- Monitors Kubernetes resources (Pods, Deployments)
- Detects incidents via field/annotation watchers
- Triggers AI analysis workflow
- Manages shadow verification daemons

**Key Handlers:**
- `handle_pod_phase_change()` - Detects pod failures
- `handle_deployment_unavailable_replicas()` - Detects deployment issues
- `shadow_verification_daemon()` - Long-running shadow testing

### 5.2 Agent Workflow (`src/aegis/agent/graph.py`)

**Technology:** LangGraph (state machine for AI agents)

**Workflow:**
```
START → RCA Agent → Solution Agent → Verifier Agent → END
```

**State Management:**
- `IncidentState` - Shared state between agents
- Contains: K8sGPT analysis, RCA result, fix proposal, verification plan

**Agents:**
1. **RCA Agent** (`src/aegis/agent/agents/rca_agent.py`)
   - Analyzes root cause using LLM + K8sGPT
   - Returns confidence score

2. **Solution Agent** (`src/aegis/agent/agents/solution_agent.py`)
   - Generates fix proposals (YAML, commands)
   - Assesses risk level

3. **Verifier Agent** (`src/aegis/agent/agents/verifier_agent.py`)
   - Creates verification plan
   - Specifies security tests, load tests

### 5.3 Shadow Manager (`src/aegis/shadow/manager.py`)

**Technology:** Kubernetes Python Client + vCluster

**Key Methods:**
- `create_shadow()` - Creates isolated namespace, clones resources
- `run_verification()` - Applies changes, monitors health
- `cleanup()` - Deletes shadow environment

**Security Features:**
- Resource quotas (prevents resource exhaustion)
- Network policies (isolates shadow from production)
- Auto-cleanup (ephemeral environments)

### 5.4 K8sGPT Integration (`src/aegis/agent/analyzer.py`)

**Technology:** K8sGPT CLI + Python wrapper

**Purpose:**
- Analyzes Kubernetes cluster state
- Identifies problems (Pod crashes, resource issues)
- Provides structured diagnostics to LLM agents

**Usage:**
```python
analyzer = get_k8sgpt_analyzer()
result = await analyzer.analyze("Pod", "nginx-crashloop", "default")
# Returns: K8sGPTAnalysis with problems, errors, recommendations
```

---

## 6. Security Integration Points {#security-integration-points}

### 6.1 Where Security Scans Are Called

**Primary Integration Point:** `src/aegis/shadow/manager.py`

**Current Code:**
```python
async def run_verification(self, shadow_id: str, changes: dict) -> bool:
    # Apply changes
    await self._apply_changes(env, changes)
    
    # Monitor health
    health_score = await self._monitor_health(env, duration)
    
    # TODO: Add security scanning here
    # - Trivy scan
    # - ZAP scan
    # - Falco monitoring
    
    return passed
```

**What You Need to Add:**
```python
# In run_verification(), after _apply_changes():

# 1. Trivy scan
from aegis.security.trivy import TrivyScanner
trivy = TrivyScanner()
trivy_result = await trivy.scan_image(changes.get("image"))
if not trivy_result["passed"]:
    env.status = ShadowStatus.FAILED
    return False

# 2. ZAP scan (if service is exposed)
from aegis.security.zap import ZAPScanner
zap = ZAPScanner()
zap_result = await zap.baseline_scan(shadow_service_url)
if not zap_result["passed"]:
    env.status = ShadowStatus.FAILED
    return False

# 3. Falco monitoring (already running via DaemonSet)
# Just check for alerts during verification period
```

### 6.2 Security Settings Integration

**Location:** `src/aegis/config/settings.py`

**Already Defined:**
```python
class SecuritySettings(BaseSettings):
    trivy_enabled: bool = Field(default=True)
    zap_enabled: bool = Field(default=True)
    falco_enabled: bool = Field(default=True)
    # ... more settings
```

**Usage:**
```python
from aegis.config.settings import settings

if settings.security.trivy_enabled:
    # Run Trivy scan
    pass
```

### 6.3 Metrics Integration

**Location:** `src/aegis/observability/_metrics.py`

**Add Security Metrics:**
```python
# Security scan metrics
security_scans_total = Counter(
    "aegis_security_scans_total",
    "Total security scans performed",
    ["scanner", "status"]
)

security_vulnerabilities_found = Gauge(
    "aegis_security_vulnerabilities_found",
    "Number of vulnerabilities found",
    ["scanner", "severity"]
)
```

---

## 7. Getting Started Checklist

### For Security Engineers

1. **Review Architecture:**
   ```bash
   cat docs/architecture/AEGIS_DESIGN_BLUEPRINT.md
   cat docs/SECURITY_ENGINEER_GUIDE.md
   ```

2. **Check Current Security Code:**
   ```bash
   ls -la src/aegis/security/
   # Currently: Only __init__.py exists (empty)
   ```

3. **Install Security Tools:**
   ```bash
   # Trivy
   curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | \
     sh -s -- -b /usr/local/bin
   
   # OWASP ZAP (Docker)
   docker pull owasp/zap2docker-stable
   
   # Falco
   helm repo add falcosecurity https://falcosecurity.github.io/charts
   helm install falco falcosecurity/falco --namespace aegis-security --create-namespace
   ```

4. **Start Implementing:**
   ```bash
   # Create security modules
   touch src/aegis/security/trivy.py
   touch src/aegis/security/zap.py
   mkdir -p src/aegis/security/exploit
   touch src/aegis/security/exploit/sandbox.py
   ```

5. **Test Integration:**
   ```bash
   # Run unit tests
   make test-unit
   
   # Run security checks
   make security
   ```

---

## 8. Summary

### What AEGIS Does

1. **Detects** Kubernetes incidents automatically
2. **Analyzes** root causes using AI (K8sGPT + LLM)
3. **Proposes** fixes using AI reasoning
4. **Tests** fixes in isolated shadow environments
5. **Verifies** security, performance, functionality
6. **Deploys** only after passing all tests

### Your Role as Security Engineer

**You are responsible for:**
- ✅ Implementing security scanning (Trivy, ZAP, Falco)
- ✅ Securing shadow environments (isolation, RBAC, network policies)
- ✅ Creating exploit sandboxes (gVisor integration)
- ✅ Building security scenarios (SQL injection, JWT exploits)
- ✅ Ensuring zero-trust testing (no production risk)

**Your code ensures that every fix proposed by AEGIS is:**
- ✅ Scanned for vulnerabilities
- ✅ Tested for security issues
- ✅ Verified in isolated environments
- ✅ Safe to deploy to production

**You are the security gatekeeper for autonomous incident response!** 🛡️

---

*Last updated: January 2026*
