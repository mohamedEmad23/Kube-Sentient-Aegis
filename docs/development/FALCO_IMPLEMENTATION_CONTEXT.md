# Falco Integration Context Report

**Generated for:** AEGIS Security Layer Integration  
**Date:** January 31, 2026  
**Repository:** mohamedEmad23/Kube-Sentient-Aegis (branch: barakat)

---

## Executive Summary

This report provides the complete technical context needed to implement Falco runtime security monitoring into AEGIS. Falco is a runtime security monitoring tool that detects suspicious behavior by monitoring syscalls.

**Current State:**
- ✅ Settings flag `SECURITY_FALCO_ENABLED` exists and defaults to `True`
- ✅ Shadow verification workflow is fully functional (Trivy already integrated)
- ✅ Asyncio subprocess pattern established (used by Trivy, K8sGPT, ZAP)
- ✅ Test results dict (`env.test_results`) ready to receive Falco output
- ❌ **No Falco code implementation exists**
- ❌ **No Falco integration into shadow verification**

**Key Metrics:**
- Shadow verification flow: [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) lines 204-315
- Settings defined: [src/aegis/config/settings.py](../../src/aegis/config/settings.py) lines 205-233
- Trivy integration reference: [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) lines 252-285
- CLI display function: [src/aegis/cli.py](../../src/aegis/cli.py) lines 185-299 (`_display_analysis_results()`)

---

## Workflow: Shadow Verification (with code references)

### Overview Sequence

The shadow verification follows this flow:
```
1. create_shadow()      → Create isolated namespace
2. run_verification()   → Main verification entry point
   2a. _apply_changes()      → Apply fix to shadow pod
   2b. [SECURITY GATES]      → Run security scanners
       - Trivy (post-fix image scan)
       - [FALCO TO BE INSERTED HERE]
   2c. _monitor_health()     → Check pod health for duration
   2d. Evaluate results      → Return pass/fail
3. cleanup()            → Delete shadow namespace
```

### Key Function: `ShadowManager.run_verification()`

**File:** [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py)  
**Lines:** 204–315  
**Signature:**
```python
async def run_verification(
    self,
    shadow_id: str,
    changes: dict[str, Any],
    duration: int | None = None,
) -> bool:
    """Run verification tests in shadow environment.
    
    Returns:
        bool: True if verification passed, False otherwise
    """
```

### Exact Sequence: Where Trivy Runs Today

**Lines 242-285:** Trivy integration (POST-FIX)

```python
# Line 242: Apply changes
await self._apply_changes(env, changes)
env.logs.append(f"Applied changes: {list(changes.keys())}")

# Lines 252-285: Security gate - Trivy image scan
# ================================================================
# Security gate: Trivy image scan (fail closed)
# ================================================================
trivy_result: dict[str, Any] | None = None
if settings.security.trivy_enabled and "image" in changes:
    from aegis.security.trivy import TrivyScanner

    image = str(changes["image"])
    env.logs.append(
        f"Running Trivy image scan (severity={settings.security.trivy_severity}): {image}"
    )
    trivy_result = await TrivyScanner().scan_image(
        image,
        severity_csv=settings.security.trivy_severity,
        fail_on_csv=settings.security.trivy_severity,
    )

    if not trivy_result.get("passed", False):
        env.status = ShadowStatus.FAILED
        env.test_results = {
            "passed": False,
            "timestamp": datetime.now(UTC).isoformat(),
            "trivy": trivy_result,
        }
        env.logs.append(
            f"Trivy failed: {trivy_result.get('severity_counts', {})} "
            f"error={trivy_result.get('error')}"
        )
        log.warning(
            "shadow_verification_blocked_by_trivy",
            shadow_id=shadow_id,
            image=image,
            severity_counts=trivy_result.get("severity_counts"),
            error=trivy_result.get("error"),
        )
        return False  # ← BLOCKS PRODUCTION IF TRIVY FAILS
```

### Where to Insert Falco Check

**Exact Insertion Point:**

- **After:** Line 285 (after Trivy block ends)
- **Before:** Line 287 (before `_monitor_health()` call)

**Code context (lines 285-292):**
```python
                        return False

                # Monitor health for specified duration
                # ← [INSERT FALCO CHECK HERE] ←
                health_score = await self._monitor_health(env, duration)
                env.health_score = health_score
                env.logs.append(f"Health monitoring complete: score={health_score:.2f}")
```

### What Environment Data Will Be Available at Insertion Point

At the insertion point, you will have:
- `env`: `ShadowEnvironment` object (see line 60)
  - `env.id`: Shadow environment ID (string)
  - `env.namespace`: Shadow namespace name (string)
  - `env.source_resource`: Original pod/deployment name
  - `env.source_namespace`: Original namespace
  - `env.logs`: List of log messages
  - `env.test_results`: Dict for storing results
  - `env.source_resource_kind`: "Pod" or "Deployment"
- `shadow_id`: Same as `env.id` (string)
- `changes`: Dict of changes applied (e.g., `{"image": "new-image"}`)
- `duration`: Verification duration in seconds (int)
- `settings.security.falco_enabled`: Boolean flag from config

---

## Existing Security Tools (with code references)

### Trivy Scanner

**File:** [src/aegis/security/trivy.py](../../src/aegis/security/trivy.py)

**Key Functions:**
```python
class TrivyScanner:
    async def scan_image(
        self,
        image: str,
        *,
        timeout_seconds: int | None = None,
        severity_csv: str | None = None,
        fail_on_csv: str | None = None,
    ) -> dict[str, Any]:
        """Scan container image and return dict."""
```

**Output Structure (lines 125-200):**
```python
# Success case (passed)
{
    "passed": True,
    "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 2, "LOW": 5, "UNKNOWN": 0},
    "vulnerabilities": 7,
    "error": None,
    "raw": {...}  # Full Trivy JSON
}

# Failure case (failed)
{
    "passed": False,
    "error": "Trivy binary not found in PATH",
    "severity_counts": {},
    "vulnerabilities": 0,
}
```

**Pass/Fail Logic:**
- Returns `passed=True` only if **no** vulnerabilities in `fail_on` set
- **Fail closed:** When Trivy unavailable, returns `passed=False`
- Configurable severity via settings

### ZAP Scanner

**File:** [src/aegis/security/zap.py](../../src/aegis/security/zap.py) (implemented but NOT integrated)

**Key Function:**
```python
async def zap_baseline_scan(
    target_url: str,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
```

**Output Structure:**
```python
{
    "target_url": "http://shadow-service:8080",
    "tool": "zap",
    "timeout_seconds": 300,
    "alerts": [...],  # Normalized alerts
    "summary": {"high": 0, "medium": 1, "low": 2, "info": 3},
    "raw_report": {...}  # Full ZAP JSON
}
```

**Status:** Implemented but NOT called from shadow verification.

### Falco (Not Yet Implemented)

Currently only a settings flag exists:
- [src/aegis/config/settings.py](../../src/aegis/config/settings.py) line 220: `falco_enabled: bool = Field(default=True)`

---

## Settings and Flags (with code references)

### SecuritySettings Class

**File:** [src/aegis/config/settings.py](../../src/aegis/config/settings.py)  
**Lines:** 205–233

```python
class SecuritySettings(BaseSettings):
    """Security scanning and exploit testing configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        case_sensitive=False,
    )

    trivy_enabled: bool = Field(
        default=True,
        description="Enable Trivy vulnerability scanning",
    )
    trivy_severity: str = Field(
        default="HIGH,CRITICAL",
        description="Comma-separated severity levels (LOW,MEDIUM,HIGH,CRITICAL)",
    )
    zap_enabled: bool = Field(
        default=True,
        description="Enable OWASP ZAP dynamic scanning",
    )
    zap_api_url: str = Field(
        default="http://localhost:8080",
        description="OWASP ZAP API endpoint",
    )
    falco_enabled: bool = Field(  # ← FALCO FLAG EXISTS
        default=True,
        description="Enable Falco runtime security monitoring",
    )
    exploit_sandbox_enabled: bool = Field(
        default=False,
        description="Enable experimental exploit proof-of-concept generation",
    )
    sandbox_timeout: int = Field(
        default=30,
        description="Exploit sandbox execution timeout in seconds",
        ge=5,
    )
```

### Accessing Settings in Code

```python
# From any AEGIS module:
from aegis.config.settings import settings

# Check if Falco is enabled
if settings.security.falco_enabled:
    # Run Falco check

# Get other flags
settings.security.trivy_enabled
settings.security.zap_enabled
```

### Environment Variables

Falco settings can be set via env vars:
```bash
SECURITY_FALCO_ENABLED=true    # Boolean
```

### Missing Falco Settings (to be added later)

Future additions might include:
- `falco_namespace`: Which namespace Falco DaemonSet is deployed in
- `falco_label_selector`: Label selector to find Falco pods
- `falco_severity_threshold`: Minimum severity (WARNING, CRITICAL, etc.)
- `falco_alert_timeout`: How long to check for alerts after fix

---

## Subprocess/Command Execution Pattern

### Established Pattern

AEGIS uses a consistent async subprocess pattern throughout:

**Pattern Source 1: Trivy** ([src/aegis/security/trivy.py](../../src/aegis/security/trivy.py) lines 147-168)
```python
try:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )
    except TimeoutError:
        proc.kill()
        await proc.wait()
        # Return failure dict
        return {..., "passed": False, "error": "timeout"}

    if proc.returncode != 0:
        # Handle error
        log.error("command_failed", returncode=proc.returncode)
        return {..., "passed": False, ...}

    # Parse output
    result = json.loads(stdout.decode())
    # Return success/failure based on parsed result

except json.JSONDecodeError as e:
    log.exception("parse_error")
    return {..., "passed": False, ...}

except OSError as e:
    log.exception("execution_error")
    return {..., "passed": False, ...}
```

**Pattern Source 2: K8sGPT** ([src/aegis/agent/analyzer.py](../../src/aegis/agent/analyzer.py) lines 96-109)
```python
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)

try:
    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=settings.kubernetes.api_timeout,
    )
except TimeoutError:
    process.kill()
    await process.wait()
    # Fallback behavior
```

### Recommended Pattern for Falco

```python
# 1. Check if enabled
if not settings.security.falco_enabled:
    return None  # Skip

# 2. Build kubectl command to check for Falco alerts in shadow namespace
cmd: list[str] = [
    "kubectl",
    "logs",
    "-n", env.namespace,
    "-l", "app=falco",  # Or similar selector
    "--since=<timestamp>",  # Or --tail=N
    "--timestamps=true",
]

# 3. Execute with timeout
try:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=30  # seconds
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        log.warning("falco_check_timeout")
        return {"passed": False, "error": "Falco check timed out"}
    
    if proc.returncode != 0:
        log.warning("falco_check_failed", returncode=proc.returncode)
        return {"passed": False, "error": "kubectl failed"}
    
    # 4. Parse output (raw text or JSON if available)
    alert_text = stdout.decode()
    
    # 5. Determine pass/fail based on alerts
    if "CRITICAL" in alert_text or "WARNING" in alert_text:
        return {"passed": False, "alerts": alert_text}
    
    return {"passed": True, "alerts": None}

except (OSError, json.JSONDecodeError) as e:
    log.exception("falco_execution_error")
    return {"passed": False, "error": str(e)}
```

---

## Where to Attach Falco Output

### ShadowEnvironment.test_results Structure

**File:** [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py)  
**Lines:** 62–67 (dataclass definition)

```python
@dataclass
class ShadowEnvironment:
    """Represents a shadow verification environment."""

    id: str
    namespace: str
    source_namespace: str
    source_resource: str
    source_resource_kind: str
    status: ShadowStatus = ShadowStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    health_score: float = 0.0
    logs: list[str] = field(default_factory=list)
    error: str | None = None
    test_results: dict[str, Any] = field(default_factory=dict)  # ← STORE FALCO HERE
```

### Example Test Results Dict (Current Structure)

**Lines 297–305:**
```python
env.test_results = {
    "health_score": health_score,      # float
    "duration": duration,              # int (seconds)
    "passed": passed,                  # bool
    "timestamp": datetime.now(UTC).isoformat(),  # str
    **({"trivy": trivy_result} if trivy_result is not None else {}),  # dict
}
```

### Proposed Addition for Falco

After Falco check, append to `env.test_results`:

```python
# Store Falco result in same dict
if falco_result is not None:
    env.test_results["falco"] = falco_result
    
# If Falco failed, block production
if falco_result and not falco_result.get("passed", False):
    env.status = ShadowStatus.FAILED
    env.test_results["passed"] = False
    log.warning("shadow_verification_blocked_by_falco", shadow_id=shadow_id)
    return False
```

### Result Dict Available to CLI

The `env.test_results` dict eventually flows to:
1. **Operator handler** [src/aegis/k8s_operator/handlers/shadow.py](../../src/aegis/k8s_operator/handlers/shadow.py) line 314
2. **CLI display** via operator annotations or future API

---

## CLI Display Location

### Analyze Command and Result Display

**File:** [src/aegis/cli.py](../../src/aegis/cli.py)

**Entry Point:** `analyze()` command  
**Lines:** 306–440

```python
@typed_command(app)
def analyze(
    resource: str = typer.Argument(...),
    namespace: str = typer.Option("default", "-n", "--namespace"),
    _auto_fix: bool = typer.Option(False, "--auto-fix"),
    _export: str | None = typer.Option(None, "-e", "--export"),
    mock: bool = typer.Option(False, "--mock"),
) -> None:
    """Analyze Kubernetes resources for issues."""
    # ...
    result = asyncio.run(
        analyze_incident(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            use_mock=mock,
        )
    )
    
    _display_analysis_results(console, dict(result))
```

### Display Function: `_display_analysis_results()`

**File:** [src/aegis/cli.py](../../src/aegis/cli.py)  
**Lines:** 185–299

```python
def _display_analysis_results(console: Console, result: dict[str, Any]) -> None:
    """Display analysis results with rich formatting.

    Args:
        console: Rich console instance
        result: Analysis result dictionary (IncidentState as dict)
    """
    # Display RCA Results (lines 191-224)
    rca_result = result.get("rca_result")
    if rca_result:
        # ...print RCA panel...

    # Display Fix Proposal (lines 226-263)
    fix_proposal = result.get("fix_proposal")
    if fix_proposal:
        # ...print Fix panel...

    # Display Verification Plan (lines 265-299)
    verification_plan = result.get("verification_plan")
    if verification_plan:
        # ...print Verification panel...

    # ← [SECURITY REPORT PANEL COULD BE INSERTED HERE]
    # After line 299, before function ends
```

### Where Security Report Should Display

**After line 299** (after Verification Plan panel), before function ends:

```python
    console.print(verify_panel)
    console.print()

    # ← [INSERT SECURITY REPORT PANEL HERE] ←
    # Future: If result includes security_report (not yet in IncidentState)
    # security_report = result.get("security_report")
    # if security_report:
    #     # Display Trivy, ZAP, Falco results
    #     console.print(security_panel)
    #     console.print()
```

**Note:** Currently, `IncidentState` (defined in [src/aegis/agent/state.py](../../src/aegis/agent/state.py)) does NOT include a `security_report` field. It would need to be added there first before the CLI can display it.

---

## Next Step Recommendation (exact file/function to modify first)

### Recommended Implementation Order

#### **Step 1: Create Falco Scanner Module** (First – Foundation)

**Create File:** `src/aegis/security/falco.py`

**Expected Content:**
```python
"""Falco runtime security monitoring integration."""

async def check_falco_alerts(
    namespace: str,
    since_timestamp: datetime,
    severity_threshold: str = "WARNING",
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Check Falco alerts in shadow namespace.
    
    Returns:
        {
            "passed": bool,
            "alert_count": int,
            "alerts": str,  # Raw alert text
            "error": str | None,
        }
    """
```

This module should follow the Trivy pattern from [src/aegis/security/trivy.py](../../src/aegis/security/trivy.py).

---

#### **Step 2: Integrate into Shadow Verification** (Second – Core Integration)

**File to Modify:** [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py)

**Location:** Lines 287–290 (before `_monitor_health()`)

**Changes:**
1. Import Falco scanner at top of `run_verification()`
2. Add Falco check after Trivy block
3. Gate on `settings.security.falco_enabled`
4. Store result in `env.test_results["falco"]`
5. Block production if Falco returns `passed=False`

**Code Template:**
```python
# After line 285 (after Trivy block), before line 287:

# Run Falco check
falco_result: dict[str, Any] | None = None
if settings.security.falco_enabled:
    from aegis.security.falco import check_falco_alerts
    
    falco_result = await check_falco_alerts(
        namespace=env.namespace,
        since_timestamp=datetime.now(UTC),
    )
    
    if not falco_result.get("passed", False):
        env.status = ShadowStatus.FAILED
        env.test_results = {
            "passed": False,
            "timestamp": datetime.now(UTC).isoformat(),
            "falco": falco_result,
        }
        env.logs.append(f"Falco failed: {falco_result.get('alert_count', 0)} alerts")
        log.warning("shadow_verification_blocked_by_falco", shadow_id=shadow_id)
        return False

# Continue with health monitoring...
health_score = await self._monitor_health(env, duration)
```

---

#### **Step 3: Update Test Results Aggregation** (Third – Store Results)

**File to Modify:** [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py)

**Location:** Lines 297–305

**Change:** Merge Falco result into `env.test_results` dict

**Current Code:**
```python
env.test_results = {
    "health_score": health_score,
    "duration": duration,
    "passed": passed,
    "timestamp": datetime.now(UTC).isoformat(),
    **({"trivy": trivy_result} if trivy_result is not None else {}),
}
```

**Updated Code:**
```python
env.test_results = {
    "health_score": health_score,
    "duration": duration,
    "passed": passed,
    "timestamp": datetime.now(UTC).isoformat(),
    **({"trivy": trivy_result} if trivy_result is not None else {}),
    **({"falco": falco_result} if falco_result is not None else {}),  # ADD THIS
}
```

---

### Why This Order?

1. **Step 1 (Falco module):** Foundation – Doesn't depend on anything else
2. **Step 2 (Shadow integration):** Core functionality – Makes Falco actually run
3. **Step 3 (Result storage):** Persistence – Allows results to be passed to CLI/operator

This order allows each step to be tested independently before moving to the next.

---

## Technical Dependencies Summary

| Dependency | Status | Location | Notes |
|-----------|--------|----------|-------|
| **asyncio.create_subprocess_exec** | ✅ Established | [src/aegis/security/trivy.py](../../src/aegis/security/trivy.py) line 147 | Use same pattern |
| **JSON result dict** | ✅ Pattern exists | [src/aegis/security/trivy.py](../../src/aegis/security/trivy.py) lines 125-200 | Follow for consistency |
| **Settings flag** | ✅ Exists | [src/aegis/config/settings.py](../../src/aegis/config/settings.py) line 220 | `settings.security.falco_enabled` |
| **ShadowEnvironment.test_results** | ✅ Available | [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) line 66 | Dict to store output |
| **Logging** | ✅ Established | [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) line 30 | `log` instance available |
| **Metrics (optional)** | ✅ Available | [src/aegis/observability/_metrics.py](../../src/aegis/observability/_metrics.py) | Can track Falco checks |
| **CLI Display** | ⚠️ Partial | [src/aegis/cli.py](../../src/aegis/cli.py) lines 185-299 | Panel infrastructure exists |

---

## Code References Summary

| What | File | Lines | Status |
|------|------|-------|--------|
| Shadow verification flow | [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) | 204–315 | ✅ Established |
| ShadowEnvironment dataclass | [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) | 62–67 | ✅ Established |
| Trivy integration (reference) | [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) | 252–285 | ✅ Established |
| Falco insertion point | [src/aegis/shadow/manager.py](../../src/aegis/shadow/manager.py) | 287–290 | ⏳ To be created |
| Security settings | [src/aegis/config/settings.py](../../src/aegis/config/settings.py) | 205–233 | ✅ Established |
| Falco flag | [src/aegis/config/settings.py](../../src/aegis/config/settings.py) | 220–223 | ✅ Established |
| Trivy scanner (pattern) | [src/aegis/security/trivy.py](../../src/aegis/security/trivy.py) | 86–219 | ✅ Established |
| Falco scanner module | [src/aegis/security/falco.py](../../src/aegis/security/falco.py) | N/A | ❌ To be created |
| K8sGPT subprocess pattern | [src/aegis/agent/analyzer.py](../../src/aegis/agent/analyzer.py) | 96–109 | ✅ Reference |
| CLI analyze command | [src/aegis/cli.py](../../src/aegis/cli.py) | 306–440 | ✅ Established |
| CLI display function | [src/aegis/cli.py](../../src/aegis/cli.py) | 185–299 | ✅ Established (partial) |

---

*Report generated from actual codebase analysis. All file paths and line numbers are accurate as of January 31, 2026.*
