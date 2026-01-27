# 🛡️ AEGIS Security Engineer Guide

**Your Role in the AEGIS Project**

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Your Responsibilities](#your-responsibilities)
3. [Security Architecture](#security-architecture)
4. [Implementation Tasks](#implementation-tasks)
5. [Security Tools Integration](#security-tools-integration)
6. [Shadow Verification Security](#shadow-verification-security)
7. [Threat Model & Scenarios](#threat-model--scenarios)
8. [Getting Started](#getting-started)

---

## 1. Project Overview {#project-overview}

### What is AEGIS?

**AEGIS (Autonomous SRE Agent with Shadow Verification)** is an AI-powered Kubernetes operator that:
- **Detects** production incidents automatically
- **Analyzes** root causes using LLMs (Ollama/K8sGPT)
- **Proposes** fixes using AI reasoning
- **Tests** fixes in isolated shadow environments **BEFORE** production
- **Verifies** security and performance before deployment

### Why This Matters for Security

Traditional incident response:
```
Incident → Manual Analysis → Fix → Deploy to Production → Hope it works
```

AEGIS approach:
```
Incident → AI Analysis → Proposed Fix → Shadow Environment Testing →
Security Scan → Load Test → Human Approval → Deploy to Production
```

**Key Security Benefits:**
- ✅ **Zero-trust testing** - All fixes tested in isolated sandboxes
- ✅ **Automated security scanning** - Trivy, ZAP, Falco integrated
- ✅ **Exploit verification** - Proof-of-concept generation in gVisor
- ✅ **No production risk** - Shadow environments are ephemeral

---

## 2. Your Responsibilities {#your-responsibilities}

As a **Security Engineer** on this project, you own:

### Phase 1: Foundation (Days 3-4, 7-8)
- ✅ Kubernetes cluster security hardening
- ✅ vCluster security configuration
- ✅ Network policies for shadow environments

### Phase 2: Core Security (Days 20-25)
- ✅ Shadow environment isolation (vCluster + Kata Containers)
- ✅ Verification test framework (Locust + ZAP integration)

### Phase 3: Security Integration (Days 26-35) ⭐ **YOUR MAIN PHASE**
- ✅ **Falco runtime rules** (Days 26-28)
- ✅ **Trivy scanning pipeline** (Days 29-31)
- ✅ **OWASP ZAP automation** (Days 32-34)
- ✅ **gVisor sandboxing for exploits** (Day 35)

### Phase 4: Security Scenarios (Days 39-43)
- ✅ **Scenario 2: SQL Injection** - WAF virtual patching + ZAP verification
- ✅ **Scenario 3: Insecure JWT** - Custom exploit generation

---

## 3. Security Architecture {#security-architecture}

### 3.1 Multi-Layer Isolation

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUCTION CLUSTER                     │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐  │
│  │         vCluster (Shadow Environment)              │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │      Kata Container Runtime (VM-based)        │ │  │
│  │  │  ┌───────────────────────────────────────┐  │ │  │
│  │  │  │    gVisor (Application Kernel)          │  │ │  │
│  │  │  │  ┌─────────────────────────────────┐  │  │ │  │
│  │  │  │  │  Exploit Code Execution         │  │  │ │  │
│  │  │  │  └─────────────────────────────────┘  │  │ │  │
│  │  │  └───────────────────────────────────────┘  │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Isolation Levels:**
1. **vCluster** - Namespace-level isolation (Kubernetes RBAC)
2. **Kata Containers** - Hardware-level isolation (VT-x/AMD-V)
3. **gVisor** - Application kernel (system call interception)

### 3.2 Security Tools Stack

| Tool | Purpose | Your Task |
|------|---------|-----------|
| **Trivy** | Container/K8s vulnerability scanning | Integrate into verification pipeline |
| **OWASP ZAP** | Dynamic application security testing | Automate API scanning in shadows |
| **Falco** | Runtime security monitoring | Create custom rules for AEGIS |
| **gVisor** | Exploit sandboxing | Isolate LLM-generated exploit code |
| **Kata Containers** | VM-based container isolation | Secure shadow environments |

---

## 4. Implementation Tasks {#implementation-tasks}

### 4.1 Trivy Integration (Days 29-31)

**File to Create:** `src/aegis/security/trivy.py`

```python
"""Trivy vulnerability scanner integration."""

class TrivyScanner:
    """Scan container images and Kubernetes clusters for vulnerabilities."""

    async def scan_image(self, image: str) -> dict:
        """Scan container image for vulnerabilities.

        Returns:
            {
                "vulnerabilities": [...],
                "severity_counts": {"CRITICAL": 2, "HIGH": 5},
                "passed": bool
            }
        """
        pass

    async def scan_cluster(self, namespace: str) -> dict:
        """Scan Kubernetes cluster resources."""
        pass

    def parse_results(self, json_output: str) -> dict:
        """Parse Trivy JSON output."""
        pass
```

**Integration Points:**
- Called during shadow verification
- Blocks deployment if CRITICAL/HIGH vulnerabilities found
- Reports to Prometheus metrics

**Configuration:**
```python
# In src/aegis/config/settings.py (already exists)
SECURITY_TRIVY_ENABLED=true
SECURITY_TRIVY_SEVERITY=HIGH,CRITICAL
```

### 4.2 OWASP ZAP Integration (Days 32-34)

**File to Create:** `src/aegis/security/zap.py`

```python
"""OWASP ZAP dynamic security scanning."""

class ZAPScanner:
    """Automated security testing with OWASP ZAP."""

    async def baseline_scan(self, target_url: str) -> dict:
        """Quick security scan of target URL.

        Returns:
            {
                "alerts": [...],
                "risk_counts": {"High": 2, "Medium": 5},
                "passed": bool
            }
        """
        pass

    async def api_scan(self, openapi_spec: str) -> dict:
        """API-focused security scan."""
        pass

    def parse_alerts(self, json_output: str) -> dict:
        """Parse ZAP alert JSON."""
        pass
```

**Use Cases:**
- Scan shadow environment endpoints after fix deployment
- Verify SQL injection patches work
- Test WAF rules effectiveness

**Configuration:**
```python
SECURITY_ZAP_ENABLED=true
SECURITY_ZAP_API_URL=http://localhost:8080
```

### 4.3 Falco Runtime Rules (Days 26-28)

**File to Create:** `deploy/falco/aegis-rules.yaml`

```yaml
# Custom Falco rules for AEGIS
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

**Integration:**
- Deploy Falco DaemonSet in `aegis-security` namespace
- Create custom rules for shadow environment monitoring
- Alert on suspicious activity in shadows

### 4.4 gVisor Exploit Sandbox (Day 35)

**File to Create:** `src/aegis/security/exploit/sandbox.py`

```python
"""Secure exploit execution sandbox using gVisor."""

class ExploitSandbox:
    """Execute LLM-generated exploit code safely."""

    async def execute_exploit(
        self,
        exploit_code: str,
        target_url: str,
        timeout: int = 30
    ) -> dict:
        """Execute exploit in gVisor sandbox.

        Returns:
            {
                "exploitable": bool,
                "proof_of_concept": str,
                "evidence": [...]
            }
        """
        pass
```

**Use Case:**
- When AEGIS detects insecure JWT, generate exploit PoC
- Execute exploit in gVisor (isolated from host)
- Verify vulnerability exists before proposing fix

---

## 5. Security Tools Integration {#security-tools-integration}

### 5.1 Installation Checklist

```bash
# Trivy - Vulnerability Scanner
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | \
  sh -s -- -b /usr/local/bin

# OWASP ZAP - DAST Scanner
docker pull owasp/zap2docker-stable

# Falco - Runtime Security
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco --namespace aegis-security --create-namespace

# gVisor - Container Sandbox
curl -fsSL https://gvisor.dev/install | bash
```

### 5.2 Integration Workflow

```
┌─────────────────────────────────────────────────────────┐
│              SHADOW VERIFICATION WORKFLOW                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Create Shadow Environment (vCluster)                │
│     │                                                    │
│     ▼                                                    │
│  2. Deploy Proposed Fix                                  │
│     │                                                    │
│     ▼                                                    │
│  3. Run Security Scans                                   │
│     ├─ Trivy: Scan container images                     │
│     ├─ ZAP: Scan API endpoints                         │
│     └─ Falco: Monitor runtime behavior                 │
│     │                                                    │
│     ▼                                                    │
│  4. Run Load Tests (Locust)                             │
│     │                                                    │
│     ▼                                                    │
│  5. Generate Security Report                             │
│     ├─ Vulnerabilities found?                           │
│     ├─ Security tests passed?                         │
│     └─ Performance acceptable?                          │
│     │                                                    │
│     ▼                                                    │
│  6. Approve or Reject                                   │
│     └─ If approved → Deploy to production              │
│     └─ If rejected → Generate new fix proposal         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Shadow Verification Security {#shadow-verification-security}

### 6.1 Security Requirements

**Shadow environments must:**
- ✅ Be **ephemeral** (auto-delete after verification)
- ✅ Have **network isolation** (NetworkPolicy)
- ✅ Use **resource quotas** (prevent resource exhaustion)
- ✅ Run with **least privilege** (RBAC)
- ✅ **Never** access production secrets
- ✅ **Never** write to production databases

### 6.2 vCluster Security Configuration

**File:** `examples/shadow/vcluster-template.yaml` (already exists)

Key security features:
```yaml
# Resource quotas
resourceQuota:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi

# Network policies (add these)
networkPolicy:
  - name: deny-all
    policyTypes: ["Ingress", "Egress"]
    # Allow only AEGIS operator access
```

### 6.3 Kata Containers for High-Security Workloads

When testing security-sensitive fixes (JWT, SQL injection):
- Use Kata runtime instead of default containerd
- Provides hardware-level isolation
- Prevents container escape attacks

**Configuration:**
```yaml
# In shadow deployment
runtimeClassName: kata
```

---

## 7. Threat Model & Scenarios {#threat-model--scenarios}

### 7.1 Security Scenarios You'll Implement

#### Scenario 2: SQL Injection (Days 39-41)

**Threat:**
- Application vulnerable to SQL injection
- Attacker can exfiltrate database

**AEGIS Response:**
1. Detect SQL injection vulnerability (via Falco/ZAP)
2. Generate WAF rule to block attack pattern
3. Deploy WAF rule to shadow environment
4. **ZAP scan** to verify protection
5. Load test to ensure no performance impact
6. Deploy to production

**Your Tasks:**
- Integrate ZAP into verification pipeline
- Create SQL injection test cases
- Verify WAF rules effectiveness

#### Scenario 3: Insecure JWT (Days 42-43)

**Threat:**
- JWT tokens use weak algorithm (HS256 with predictable secret)
- Attacker can forge tokens

**AEGIS Response:**
1. Detect insecure JWT configuration
2. Generate exploit PoC (in gVisor sandbox)
3. Verify vulnerability exists
4. Propose fix (upgrade to RS256, rotate secret)
5. Test fix in shadow environment
6. Deploy to production

**Your Tasks:**
- Implement exploit sandbox (gVisor)
- Create JWT exploit generator
- Verify fix effectiveness

### 7.2 Security Testing Checklist

For each proposed fix, verify:

- [ ] **Container Security**
  - [ ] No CRITICAL/HIGH vulnerabilities (Trivy)
  - [ ] Base image is up-to-date
  - [ ] No secrets in image layers

- [ ] **Application Security**
  - [ ] No SQL injection (ZAP)
  - [ ] No XSS vulnerabilities (ZAP)
  - [ ] Authentication/authorization working (ZAP)
  - [ ] API endpoints secured (ZAP)

- [ ] **Runtime Security**
  - [ ] No suspicious process execution (Falco)
  - [ ] No unauthorized file access (Falco)
  - [ ] No network anomalies (Falco)

- [ ] **Performance**
  - [ ] Load test passed (Locust)
  - [ ] No memory leaks
  - [ ] Response times acceptable

---

## 8. Getting Started {#getting-started}

### 8.1 Your First Tasks

1. **Review Security Architecture**
   ```bash
   cat docs/architecture/AEGIS_DESIGN_BLUEPRINT.md
   ```

2. **Check Current Security Code**
   ```bash
   ls -la src/aegis/security/
   # Currently: Only __init__.py exists (empty)
   ```

3. **Install Security Tools**
   ```bash
   # Trivy
   curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | \
     sh -s -- -b /usr/local/bin

   # Test Trivy
   trivy image python:3.12-slim
   ```

4. **Set Up OWASP ZAP**
   ```bash
   # Run ZAP in Docker
   docker run -d -p 8080:8080 owasp/zap2docker-stable zap.sh -daemon \
     -host 0.0.0.0 -port 8080 -config api.disablekey=true

   # Test ZAP API
   curl http://localhost:8080/JSON/core/view/version/
   ```

5. **Start Implementing**
   ```bash
   # Create Trivy scanner
   touch src/aegis/security/trivy.py

   # Create ZAP scanner
   touch src/aegis/security/zap.py

   # Create exploit sandbox
   mkdir -p src/aegis/security/exploit
   touch src/aegis/security/exploit/sandbox.py
   ```

### 8.2 Development Workflow

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run tests
make test-unit

# 3. Check code quality
make lint
make type-check

# 4. Run security checks
make security  # Bandit + Safety

# 5. Commit (pre-commit hooks will run)
git commit -m "feat(security): implement Trivy scanner"
```

### 8.3 Key Files to Know

| File | Purpose | Your Changes |
|------|---------|--------------|
| `src/aegis/security/` | Security package | **YOU CREATE THIS** |
| `src/aegis/config/settings.py` | Security config | Already has `SecuritySettings` |
| `src/aegis/shadow/verification.py` | Shadow testing | Integrate security scans here |
| `deploy/falco/` | Falco rules | Create custom rules |
| `examples/incidents/` | Test scenarios | Add security incident scenarios |

### 8.4 Testing Your Security Code

```python
# tests/unit/test_security_trivy.py
import pytest
from aegis.security.trivy import TrivyScanner

async def test_trivy_scan_image():
    scanner = TrivyScanner()
    result = await scanner.scan_image("python:3.12-slim")
    assert "vulnerabilities" in result
    assert result["severity_counts"]["CRITICAL"] == 0
```

---

## 9. Security Best Practices

### 9.1 Shadow Environment Security

- ✅ **Never** sync production secrets to shadows
- ✅ **Always** use resource quotas
- ✅ **Always** set network policies
- ✅ **Always** use least-privilege RBAC
- ✅ **Always** auto-delete after verification

### 9.2 Exploit Sandboxing

- ✅ **Always** use gVisor for exploit execution
- ✅ **Always** set timeouts (max 30 seconds)
- ✅ **Never** allow network access from sandbox
- ✅ **Always** log exploit attempts

### 9.3 Security Scanning

- ✅ **Always** scan before deployment
- ✅ **Block** deployment on CRITICAL vulnerabilities
- ✅ **Warn** on HIGH vulnerabilities (require approval)
- ✅ **Log** all scan results to Prometheus

---

## 10. Resources & Documentation

- **Trivy Docs:** https://aquasecurity.github.io/trivy/
- **OWASP ZAP Docs:** https://www.zaproxy.org/docs/
- **Falco Docs:** https://falco.org/docs/
- **gVisor Docs:** https://gvisor.dev/docs/
- **vCluster Docs:** https://www.vcluster.com/docs/

---

## 🎯 Summary: Your Mission

**As a Security Engineer on AEGIS, you are responsible for:**

1. ✅ **Implementing security scanning** (Trivy, ZAP, Falco)
2. ✅ **Securing shadow environments** (isolation, RBAC, network policies)
3. ✅ **Creating exploit sandboxes** (gVisor integration)
4. ✅ **Building security scenarios** (SQL injection, JWT exploits)
5. ✅ **Ensuring zero-trust testing** (no production risk)

**Your code ensures that every fix proposed by AEGIS is:**
- ✅ Scanned for vulnerabilities
- ✅ Tested for security issues
- ✅ Verified in isolated environments
- ✅ Safe to deploy to production

**You are the security gatekeeper for autonomous incident response!** 🛡️

---

*Last updated: January 2026*
