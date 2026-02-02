# Falco Runtime Verification Usage Guide

This document describes how AEGIS integrates with Falco for runtime security monitoring
in shadow verification environments.

## Overview

Falco is a cloud-native runtime security tool that monitors container syscalls and
detects suspicious behavior. AEGIS queries Falco logs during shadow verification to
detect any runtime security violations triggered by proposed changes.

## How It Works

1. When a shadow environment is created for verification, AEGIS records the start timestamp
2. After applying changes (scaling, rollback, config changes, etc.), AEGIS queries Falco logs
3. Logs are filtered to only include alerts from the shadow namespace
4. If any alerts exceed the configured severity threshold, verification fails
5. If Falco is unavailable, the check is skipped (fail-open) with a warning

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AEGIS Shadow Verification                        │
├─────────────────────────────────────────────────────────────────────┤
│  1. Create Shadow Env  →  2. Apply Changes  →  3. Security Gates   │
│                                                                     │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   │
│  │   Trivy Scan    │   │   Falco Check   │   │ Health Monitor  │   │
│  │ (Image Vulns)   │ → │ (Runtime Alerts)│ → │  (Readiness)    │   │
│  │  Fail-Closed    │   │   Fail-Open     │   │  Health Score   │   │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   kubectl logs -n falco │
                    │   -l app=falco          │
                    │   --since=Nm            │
                    └─────────────────────────┘
```

## Configuration

### Settings

Falco integration is controlled via AEGIS settings (`src/aegis/config/settings.py`):

| Setting | Default | Description |
|---------|---------|-------------|
| `security.falco_enabled` | `True` | Enable/disable Falco runtime checks |
| `security.falco_severity` | `WARNING` | Minimum severity to fail verification |
| `security.falco_namespace` | `falco` | Namespace where Falco is deployed |
| `security.falco_label_selector` | `app=falco` | Label selector for Falco pods |

### Environment Variables

```bash
# Disable Falco checks
export AEGIS_SECURITY__FALCO_ENABLED=false

# Set minimum severity to trigger failure (CRITICAL, ERROR, WARNING, etc.)
export AEGIS_SECURITY__FALCO_SEVERITY=CRITICAL
```

## Falco Cluster Requirements

For AEGIS to query Falco alerts, you need:

1. **Falco DaemonSet** installed in the cluster
2. **JSON output enabled** (recommended for structured parsing)
3. **RBAC permissions** for AEGIS to read logs from Falco namespace

### Installing Falco

Using Helm:

```bash
# Add Falco Helm repo
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

# Install Falco with JSON output
helm install falco falcosecurity/falco \
  --namespace falco \
  --create-namespace \
  --set falco.json_output=true \
  --set falco.json_include_output_property=true
```

### RBAC Requirements

AEGIS needs permission to read pod logs in the Falco namespace:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: aegis-falco-reader
rules:
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: aegis-falco-reader-binding
subjects:
- kind: ServiceAccount
  name: aegis
  namespace: aegis-system
roleRef:
  kind: ClusterRole
  name: aegis-falco-reader
  apiGroup: rbac.authorization.k8s.io
```

## Severity Levels

Falco uses the following priority levels (highest to lowest):

| Priority | Numeric | Description |
|----------|---------|-------------|
| EMERGENCY | 0 | System is unusable |
| ALERT | 1 | Immediate action required |
| CRITICAL | 2 | Critical conditions |
| ERROR | 3 | Error conditions |
| WARNING | 4 | Warning conditions |
| NOTICE | 5 | Normal but significant |
| INFO | 6 | Informational |
| DEBUG | 7 | Debug-level |

The `falco_severity` setting determines the minimum priority that triggers a failure.
For example, `falco_severity=WARNING` will fail on WARNING, ERROR, CRITICAL, ALERT, and EMERGENCY.

## Behavior Matrix

| Scenario | Behavior | Verification Result |
|----------|----------|---------------------|
| Falco not installed | Skip check, log warning | Continues (fail-open) |
| kubectl not in PATH | Skip check, log warning | Continues (fail-open) |
| No alerts in namespace | Pass | Continues |
| Alerts below threshold | Pass | Continues |
| Alerts at/above threshold | Fail | Blocked |
| kubectl times out | Skip check | Continues (fail-open) |
| `falco_enabled=False` | Skip check | Continues |

## Result Structure

The Falco check returns a structured dict stored in `ShadowEnvironment.test_results["falco"]`:

```python
{
    "tool": "falco",
    "passed": True,  # False if alerts detected
    "skipped": False,  # True if check was skipped
    "reason": None,  # Reason for skip or failure
    "namespace_filter": "shadow-abc123",
    "falco_namespace": "falco",
    "label_selector": "app=falco",
    "since_timestamp": "2024-01-15T10:30:00+00:00",
    "since_minutes": 5,
    "severity_threshold": "WARNING",
    "alert_count": 0,
    "summary": {
        "critical": 0,
        "error": 0,
        "warning": 0,
        "other": 0
    },
    "alerts": [],  # Filtered alerts (JSON objects or raw strings)
    "raw_lines_count": 42,
    "stderr": None
}
```

## Programmatic Usage

```python
from datetime import datetime, UTC
from aegis.security.falco import check_falco_alerts

# Check for alerts in a namespace since a specific time
result = await check_falco_alerts(
    namespace="shadow-mytest",
    since_timestamp=datetime.now(UTC),
    severity_threshold="ERROR",  # Only fail on ERROR and above
    timeout_seconds=30,
    falco_namespace="falco",
    label_selector="app=falco",
)

if result["skipped"]:
    print(f"Falco check skipped: {result['reason']}")
elif not result["passed"]:
    print(f"Falco detected {result['alert_count']} alerts!")
    for alert in result["alerts"]:
        print(f"  - {alert}")
else:
    print("No Falco alerts detected")
```

## Troubleshooting

### Check if Falco is Running

```bash
kubectl get pods -n falco -l app=falco
```

### View Falco Logs Manually

```bash
kubectl logs -n falco -l app=falco --since=10m
```

### Test Alert Detection

Create a test pod that triggers a Falco rule:

```bash
# This should trigger "Terminal shell in container" rule
kubectl run test-shell --rm -it --image=alpine -- sh -c "cat /etc/shadow"
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "kubectl not found" | Ensure kubectl is in PATH |
| "No pods match label selector" | Check Falco deployment labels |
| "Permission denied" | Add RBAC for log reading |
| No alerts shown | Verify Falco rules are enabled |

## Integration with Shadow Manager

The Falco check is automatically invoked during `ShadowManager.run_verification()`:

```python
async def run_verification(self, shadow_id: str, changes: dict, duration: int = None):
    # ... apply changes ...
    
    # Trivy check (fail-closed)
    if settings.security.trivy_enabled and "image" in changes:
        # ... trivy scan ...
    
    # Falco check (fail-open on missing, fail-closed on alerts)
    if settings.security.falco_enabled:
        falco_result = await check_falco_alerts(
            namespace=env.namespace,
            since_timestamp=verification_start,
            severity_threshold=settings.security.falco_severity,
        )
        if not falco_result.get("passed", True) and not falco_result.get("skipped"):
            return False  # Block verification
    
    # ... health monitoring ...
```

## See Also

- [Security Layer Status](./SECURITY_LAYER_COPILOT_STATUS.md) - Overall security layer implementation status
- [Falco Implementation Context](./FALCO_IMPLEMENTATION_CONTEXT.md) - Technical details and insertion points
- [Trivy Usage](../AEGIS_TOOLS_CATALOG.md) - Image vulnerability scanning
