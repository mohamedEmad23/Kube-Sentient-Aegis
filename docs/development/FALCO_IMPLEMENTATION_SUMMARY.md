# Falco Implementation Summary

**Status:** ✅ IMPLEMENTED  
**Date:** January 31, 2026  
**Branch:** barakat

---

## Overview

Falco runtime security monitoring has been fully integrated into the AEGIS shadow verification workflow. This implementation allows AEGIS to detect suspicious runtime behavior in shadow environments before promoting changes to production.

---

## What Was Implemented

### 1. Falco Scanner Module

**File:** `src/aegis/security/falco.py`

| Component | Description |
|-----------|-------------|
| `check_falco_alerts()` | Async function that queries Falco logs via kubectl |
| `_parse_falco_line()` | Parses JSON or raw text Falco output |
| `_filter_alerts()` | Filters alerts by namespace and severity threshold |
| `_meets_severity_threshold()` | Compares priority levels |
| `_extract_namespace_from_event()` | Extracts k8s namespace from Falco JSON |
| `_extract_priority_from_event()` | Extracts priority level from Falco JSON |
| `FALCO_PRIORITY_ORDER` | Ordered list of Falco priorities |
| `PRIORITY_LEVELS` | Numeric mapping for priority comparison |

**Function Signature:**
```python
async def check_falco_alerts(
    namespace: str,
    since_timestamp: datetime,
    severity_threshold: str = "WARNING",
    timeout_seconds: int = 30,
    falco_namespace: str = "falco",
    label_selector: str = "app=falco",
    fallback_since_minutes: int = 10,
) -> dict[str, Any]
```

**Return Structure:**
```python
{
    "tool": "falco",
    "passed": bool,
    "skipped": bool,
    "reason": str | None,
    "namespace_filter": str,
    "falco_namespace": str,
    "label_selector": str,
    "since_timestamp": str,
    "since_minutes": int,
    "severity_threshold": str,
    "alert_count": int,
    "summary": {"critical": int, "error": int, "warning": int, "other": int},
    "alerts": list,
    "raw_lines_count": int,
    "stderr": str | None,
}
```

---

### 2. Shadow Manager Integration

**File:** `src/aegis/shadow/manager.py`

**Changes Made:**

1. Added `verification_start = datetime.now(UTC)` at the beginning of `run_verification()` to track when verification started

2. Inserted Falco security gate after Trivy scan block:
```python
# Security gate: Falco runtime alerts (fail open on tool missing)
falco_result: dict[str, Any] | None = None
if settings.security.falco_enabled:
    from aegis.security.falco import check_falco_alerts
    
    falco_result = await check_falco_alerts(
        namespace=env.namespace,
        since_timestamp=verification_start,
        severity_threshold=settings.security.falco_severity,
        falco_namespace=settings.security.falco_namespace,
        label_selector=settings.security.falco_label_selector,
    )
    
    if falco_result.get("skipped", False):
        env.logs.append(f"Falco check skipped: {falco_result.get('reason')}")
    elif not falco_result.get("passed", True):
        env.status = ShadowStatus.FAILED
        return False
```

3. Updated `test_results` dict to include Falco results alongside Trivy results

---

### 3. Configuration Settings

**File:** `src/aegis/config/settings.py`

**New Settings Added:**

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `falco_severity` | `str` | `"WARNING"` | Minimum priority to fail verification |
| `falco_namespace` | `str` | `"falco"` | Namespace where Falco is deployed |
| `falco_label_selector` | `str` | `"app=falco"` | Label selector for Falco pods |

**Environment Variables:**
```bash
AEGIS_SECURITY__FALCO_ENABLED=true
AEGIS_SECURITY__FALCO_SEVERITY=WARNING
AEGIS_SECURITY__FALCO_NAMESPACE=falco
AEGIS_SECURITY__FALCO_LABEL_SELECTOR=app=falco
```

---

### 4. Package Exports

**File:** `src/aegis/security/__init__.py`

Added `check_falco_alerts` to public exports:
```python
from aegis.security.falco import check_falco_alerts

__all__ = ["check_falco_alerts", "TrivyScanResult", "TrivyScanner"]
```

---

### 5. Unit Tests

**File:** `tests/unit/test_falco.py`

| Test Class | Coverage |
|------------|----------|
| `TestPriorityHelpers` | Priority level ordering and comparison |
| `TestEventParsing` | JSON/text parsing, namespace/priority extraction |
| `TestFilterAlerts` | Namespace filtering, severity filtering |
| `TestCheckFalcoAlerts` | Main function with mocked subprocess |
| `TestIntegrationScenarios` | Realistic shadow verification scenarios |

**Test Cases:**
- Falco disabled returns skipped
- kubectl not found returns skipped
- kubectl success with no alerts passes
- kubectl success with alerts fails
- kubectl failure returns skipped
- kubectl timeout returns skipped
- Typical shadow verification (no issues)
- Typical shadow verification (attack detected)

---

### 6. Documentation

**File:** `docs/development/FALCO_USAGE.md`

Complete usage guide including:
- Architecture diagram
- Configuration options
- Falco cluster requirements
- Helm installation instructions
- RBAC requirements
- Severity level reference
- Behavior matrix
- Result structure
- Programmatic usage examples
- Troubleshooting guide

---

## Behavior Summary

### Fail-Open vs Fail-Closed

| Condition | Behavior | Result |
|-----------|----------|--------|
| `falco_enabled=False` | Skip check | Verification continues |
| kubectl not in PATH | Skip check + warning | Verification continues |
| Falco pods not found | Skip check + warning | Verification continues |
| kubectl times out | Skip check + warning | Verification continues |
| No alerts detected | Pass | Verification continues |
| Alerts below threshold | Pass | Verification continues |
| **Alerts at/above threshold** | **Fail** | **Verification blocked** |

---

## Verification Flow

```
ShadowManager.run_verification()
│
├─► Apply changes to shadow environment
│
├─► [Gate 1] Trivy Image Scan (if image change)
│   ├── Fail-closed: blocks on vulnerabilities
│   └── Continue if passed
│
├─► [Gate 2] Falco Runtime Check ← NEW
│   ├── Fail-open: skips if tool missing
│   ├── Fail-closed: blocks on alerts detected
│   └── Continue if passed or skipped
│
├─► Health Monitoring (duration-based)
│
└─► Return verification result
```

---

## Files Changed Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/aegis/security/falco.py` | Created | ~320 lines |
| `src/aegis/security/__init__.py` | Modified | +2 lines |
| `src/aegis/shadow/manager.py` | Modified | +40 lines |
| `src/aegis/config/settings.py` | Modified | +12 lines |
| `tests/unit/test_falco.py` | Created | ~280 lines |
| `docs/development/FALCO_USAGE.md` | Created | ~250 lines |

---

## How to Use

### Enable/Disable Falco Checks

```python
# In code
from aegis.config.settings import settings
settings.security.falco_enabled = True

# Via environment
export AEGIS_SECURITY__FALCO_ENABLED=false
```

### Direct API Usage

```python
from datetime import datetime, UTC
from aegis.security.falco import check_falco_alerts

result = await check_falco_alerts(
    namespace="shadow-myapp-abc123",
    since_timestamp=datetime.now(UTC),
    severity_threshold="ERROR",
)

if result["passed"]:
    print("No Falco alerts detected")
elif result["skipped"]:
    print(f"Check skipped: {result['reason']}")
else:
    print(f"BLOCKED: {result['alert_count']} alerts found")
```

---

## Dependencies

- **kubectl**: Must be in PATH for log querying
- **Falco DaemonSet**: Must be deployed in cluster
- **RBAC**: AEGIS ServiceAccount needs pod/log read access

---

## Not Implemented (Out of Scope)

- Falco sidecar injection
- Custom Falco rules management
- Falco gRPC API integration
- Real-time streaming (only queries logs after-the-fact)
- Pydantic models for results (uses simple dict per requirements)
