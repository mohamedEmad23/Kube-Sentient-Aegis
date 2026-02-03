# Security Layer Baseline Analysis

**Generated from current codebase.** Analysis-only; no code changes.  
**Environment:** WSL (Ubuntu) for tool execution (Trivy, ZAP, Falco).

---

## 1) Repo Security-Related Inventory

### 1.1 `src/aegis/security/`

| File | Purpose | Key Functions/Classes | TODOs / Scaffolding |
|------|---------|------------------------|---------------------|
| `src/aegis/security/__init__.py` | Package init; exports security scanners | Re-exports `TrivyScanner`, `TrivyScanResult` | None |
| `src/aegis/security/trivy.py` | Async Trivy CLI wrapper and JSON parser for shadow gating | `_normalize_severity_list()`, `TrivyScanResult`, `TrivyScanResult.from_trivy_json()`, `TrivyScanner.scan_image()` | None. **Evaluated:** correctly implemented; fail-closed when Trivy missing or scan fails; async `asyncio.create_subprocess_exec`; WSL-friendly (no Windows-specific code). |

**trivy.py evaluation (teammate implementation):**
- Uses `shutil.which("trivy")` and returns structured failure when not in PATH.
- `TrivyScanResult.from_trivy_json()` parses `Results[].Vulnerabilities[]` and builds severity counts; pass/fail driven by `fail_on` set.
- `TrivyScanner.scan_image()` uses `asyncio.create_subprocess_exec`, timeout, and catches `JSONDecodeError`/`OSError`/`TimeoutError`; returns dict suitable for `ShadowEnvironment.test_results`.
- Settings: `settings.security.trivy_enabled`, `settings.security.trivy_severity` (config in `src/aegis/config/settings.py`).
- No shared subprocess helper; implementation is self-contained and suitable for WSL.

### 1.2 `src/aegis/shadow/`

| File | Purpose | Key Functions/Classes | TODOs / Scaffolding |
|------|---------|------------------------|---------------------|
| `src/aegis/shadow/manager.py` | Shadow env lifecycle and verification (create, apply changes, health, cleanup) | `ShadowStatus`, `ShadowEnvironment`, `ShadowManager`, `get_shadow_manager()`; `create_shadow()`, `run_verification()`, `cleanup()`, `_apply_changes()`, `_monitor_health()` | Trivy already integrated **after** `_apply_changes()` when `"image" in changes`; no baseline (pre-fix) scan; no ZAP/Falco; no structured `SecurityReport` in state. |

**Note:** There is no `src/aegis/shadow/verification.py`; verification logic lives in `ShadowManager.run_verification()`.

### 1.3 `src/aegis/k8s_operator/`

| File | Purpose | Key Functions/Classes | TODOs / Scaffolding |
|------|---------|------------------------|---------------------|
| `src/aegis/k8s_operator/handlers/shadow.py` | Operator entrypoints for shadow testing and scaling | `shadow_verification_daemon()`, `periodic_health_check_timer()`, `ai_driven_scaling_timer()`, `_run_shadow_verification()`, `_predict_load()` | `_run_shadow_verification()` delegates to `ShadowManager`; no security-specific hooks; in-memory `_ai_proposals` / `_shadow_results` (TODO in file: replace with Redis/etcd for multi-instance). |
| `src/aegis/k8s_operator/handlers/incident.py` | Incident detection and AEGIS workflow trigger | `handle_pod_phase_change()`, `handle_deployment_unavailable_replicas()`, `_analyze_pod_incident()`, `_analyze_deployment_incident()` | Calls `analyze_incident()`; does not run shadow or security; no security-related logic. |
| `src/aegis/k8s_operator/handlers/index.py` | Kopf indexes for pods/deployments/services/nodes | `pod_health_index()`, `deployment_replica_index()`, `service_endpoint_index()`, `node_resource_index()` | No security-related indexes. |

### 1.4 `src/aegis/agent/state.py` (and “wherever models are”)

| Item | Purpose | Key Types | TODOs / Scaffolding |
|------|---------|------------|---------------------|
| **IncidentState** | LangGraph shared state | TypedDict with `k8sgpt_*`, `rca_result`, `fix_proposal`, `verification_plan`, `shadow_env_id`, `shadow_test_passed`, `shadow_logs`, `messages`, etc. | No `security_report`, `security_passed`, or `security_baseline` in state. |
| **VerificationPlan** | Verifier agent output | `verification_type`, `analysis_steps`, `test_scenarios`, `success_criteria`, `duration`, `load_test_config`, **`security_checks: list[str]`** (default `[]`), `rollback_on_failure`, `approval_required` | `security_checks` exists but is “currently disabled in MVP” (see field docstring); not yet wired to security runners. |
| **FixProposal** | Solution agent output | `fix_type`, `description`, `commands`, **`manifests: dict[str, str]`**, `rollback_commands`, `estimated_downtime`, `risks`, `prerequisites`, `confidence_score` | Has `commands` and `manifests`; sufficient for shadow “changes” and for feeding scanners (e.g. image from manifests/commands). |

**Where models live:** All workflow and agent data models are in `src/aegis/agent/state.py` (no separate “models” package for this).

### 1.5 `src/aegis/config/settings.py`

| Item | Purpose | Relevant Names | TODOs / Scaffolding |
|------|---------|----------------|---------------------|
| **SecuritySettings** | Security tool toggles and params | `trivy_enabled`, `trivy_severity`, `zap_enabled`, `zap_api_url`, `falco_enabled`, `exploit_sandbox_enabled`, `sandbox_timeout` | All present; ZAP/Falco/exploit flags exist but no callers in security package yet. |

### 1.6 `src/aegis/utils/`

| File | Purpose | Key Functions/Classes | TODOs / Scaffolding |
|------|---------|------------------------|---------------------|
| `src/aegis/utils/__init__.py` | Package init | Empty package docstring | No subprocess or security helpers. |
| `src/aegis/utils/gpu.py` | GPU utilities | (File is empty) | No subprocess helpers. |

**Subprocess usage in repo:**  
- `src/aegis/security/trivy.py`: `asyncio.create_subprocess_exec` for Trivy.  
- `src/aegis/agent/analyzer.py`: `asyncio.create_subprocess_exec` for K8sGPT.  
There is no shared “subprocess helper” module; each caller implements its own.

### 1.7 Docs related to security or verification

| File | Purpose |
|------|---------|
| `docs/SECURITY_ENGINEER_GUIDE.md` | Security roles, tools (Trivy/ZAP/Falco/gVisor), integration workflow, config, and tasks. |
| `docs/PROJECT_OVERVIEW_AND_WORKFLOW.md` | System workflow, shadow verification, and security integration points. |
| `docs/development/` | Contains `AUDIT_PLAN.md`, `CLI_LLM_INTEGRATION_ARCHITECTURE.md`, `DEMO_INFRASTRUCTURE.md`, etc.; none are security-specific. This baseline lives in `docs/development/SECURITY_LAYER_BASELINE_ANALYSIS.md`. |

---

## 2) Where to Integrate Security in the Workflow

### 2.1 Shadow verification entrypoints

| Entrypoint | File | Function | How it’s used |
|------------|------|----------|----------------|
| **Operator shadow path** | `src/aegis/k8s_operator/handlers/shadow.py` | `shadow_verification_daemon()` | Daemon runs `_run_shadow_verification()` when `_ai_proposals` has a proposal for the deployment. |
| **Operator shadow impl** | `src/aegis/k8s_operator/handlers/shadow.py` | `_run_shadow_verification(deployment_name, namespace, proposal, stopped)` | Creates shadow via `get_shadow_manager().create_shadow()`, then `shadow_manager.run_verification(shadow_env.id, proposal["changes"], duration)`, then `cleanup()`. **This is the single place that “creates shadow, applies fix, and decides success/failure” in the operator.** |
| **Shadow execution** | `src/aegis/shadow/manager.py` | `ShadowManager.run_verification(shadow_id, changes, duration)` | Applies changes, runs Trivy (when `"image" in changes`), monitors health, sets `env.status` and `env.test_results`, returns `passed: bool`. |

**Exact functions that create shadow, apply fixes, and decide success/failure:**
- **Create shadow:** `ShadowManager.create_shadow()` — `src/aegis/shadow/manager.py`
- **Apply fixes:** `ShadowManager._apply_changes(env, changes)` — called inside `run_verification()` — `src/aegis/shadow/manager.py`
- **Decide success/failure:** `ShadowManager.run_verification()` — returns `bool`; also sets `env.status` (e.g. `ShadowStatus.FAILED`) and `env.test_results` — `src/aegis/shadow/manager.py`

The CLI `aegis analyze` path does **not** run shadow verification; it only runs the LangGraph workflow (`analyze_incident()`) and prints RCA / Fix / Verification Plan via `_display_analysis_results()`. So “production apply” gating today is entirely in the operator path: `_run_shadow_verification` → `run_verification()`.

### 2.2 Insertion points for security

#### A) Baseline scan before fix is applied

- **Goal:** Scan the **current** (pre-fix) asset before applying the fix (e.g. current image before switching to a new image).
- **Place:** `src/aegis/shadow/manager.py`, inside `run_verification()`, **before** `_apply_changes(env, changes)`.
- **Relevant snippet (context only; no edits in this analysis):**

```python
# src/aegis/shadow/manager.py, in run_verification(), before "Apply changes to shadow environment"

env.status = ShadowStatus.TESTING
env.logs.append("Starting verification tests")
duration = duration or self.verification_timeout

# ---- INSERTION A: Baseline security scan (e.g. current image) ----
# If changes contain "image", optionally run Trivy on the *current* deployment
# image (read from env) and store in env.test_results["baseline_scan"].
# Function to call: e.g. TrivyScanner().scan_image(current_image) or a new
# run_baseline_scans(env, shadow_id) that returns a dict to merge into test_results.
# ----

# Determine fix type from changes
fix_type = "unknown"
if "replicas" in changes:
    ...
```

- **Exact location:** Immediately after `duration = duration or self.verification_timeout` and before the “Determine fix type from changes” block; and before the existing block that calls `_apply_changes(env, changes)`.

#### B) Post-fix scan after fix

- **Goal:** Scan the **new** asset after the fix is applied (e.g. new image after patch).
- **Place:** `src/aegis/shadow/manager.py`, inside `run_verification()`, **after** `_apply_changes(env, changes)` and **before** health monitoring.
- **Current behavior:** Trivy already runs here when `settings.security.trivy_enabled` and `"image" in changes`. Code location:

```python
# src/aegis/shadow/manager.py, lines ~244–285 (inside run_verification, after _apply_changes)

await self._apply_changes(env, changes)
env.logs.append(f"Applied changes: {list(changes.keys())}")

# ----------------------------------------------------------------
# Security gate: Trivy image scan (fail closed)
# ----------------------------------------------------------------
trivy_result: dict[str, Any] | None = None
if settings.security.trivy_enabled and "image" in changes:
    ...
    trivy_result = await TrivyScanner().scan_image(...)
    if not trivy_result.get("passed", False):
        env.status = ShadowStatus.FAILED
        env.test_results = {...}
        return False
# ---- INSERTION B (extend here): ZAP/Falco post-fix scans ----
# e.g. ZAP baseline_scan(shadow_service_url), Falco alert check, and merge
# into env.test_results; gate on security_passed.
# ----

# Monitor health for specified duration
health_score = await self._monitor_health(env, duration)
```

- **Exact function + file:** `ShadowManager.run_verification()` in `src/aegis/shadow/manager.py`, after the existing Trivy block and before `_monitor_health()`.

#### C) Gating logic to block production apply

- **Goal:** Ensure production is not applied when security checks fail.
- **Place (operator):** Success/failure is already decided in `run_verification()`; the operator uses its return value in `_run_shadow_verification()`:

```python
# src/aegis/k8s_operator/handlers/shadow.py, ~lines 314–322

passed = await shadow_manager.run_verification(
    shadow_id=shadow_env.id,
    changes=changes,
    duration=settings.shadow.verification_timeout,
)
# ...
else:
    return passed  # True => allow production; False => block
```

- **Insertion for security gating:** Keep all security “fail” logic inside `run_verification()` (e.g. Trivy/ZAP/Falco setting `passed=False` and `env.status = ShadowStatus.FAILED`). No change needed in `_run_shadow_verification` signature; it already gates on `passed`.
- **Optional (CLI):** If CLI ever runs shadow (or receives a security result), gating would be “do not proceed to apply” when `security_passed` is False; that would be in whatever future function runs shadow from the CLI and then applies to production.

**Summary table**

| Insertion | Purpose | File | Function | Where |
|-----------|---------|------|----------|--------|
| A | Baseline scan before fix | `src/aegis/shadow/manager.py` | `run_verification()` | Before `_apply_changes(env, changes)` |
| B | Post-fix scan (extend existing Trivy) | `src/aegis/shadow/manager.py` | `run_verification()` | After current Trivy block, before `_monitor_health()` |
| C | Gating | Same | `run_verification()` | Keep all “fail” outcomes here; operator already gates on return value of `run_verification()` in `_run_shadow_verification()` |

---

## 3) Current Data Models and What Must Be Added

### 3.1 What already exists

| Model / field | Location | Security-related? |
|---------------|----------|--------------------|
| **VerificationPlan** | `src/aegis/agent/state.py` | Yes: `security_checks: list[str] = Field(default_factory=list, ...)` — “Security checks to perform (currently disabled in MVP)”. |
| **FixProposal** | `src/aegis/agent/state.py` | Has `commands`, `manifests`; used to build `changes` for shadow. No security-specific fields. |
| **IncidentState** | `src/aegis/agent/state.py` | Has `shadow_env_id`, `shadow_test_passed`, `shadow_logs`. No `security_report` or `security_passed`. |
| **ShadowEnvironment.test_results** | `src/aegis/shadow/manager.py` (dataclass) | Dict that already stores `trivy` (and optionally `passed`, `timestamp`). No typed `SecurityReport`; Trivy result is ad-hoc dict. |

### 3.2 What’s missing and where to add it

| Missing item | Add where | Section / note |
|--------------|-----------|------------------|
| **SecurityFinding** (e.g. one vuln/alert) | New or existing module under `src/aegis/security/` (e.g. `src/aegis/security/models.py` or in `trivy.py`/`zap.py` as a small dataclass) | Single finding: severity, title, source (Trivy/ZAP/Falco), raw id/link. |
| **SecurityReport** | Same as above | Aggregate type: `passed: bool`, `findings: list[SecurityFinding]`, `summary: dict[str, int]` (e.g. by severity), `scanner_results: dict[str, Any]` (per-scanner detail). |
| **IncidentState.security_report** | `src/aegis/agent/state.py`, in `IncidentState` TypedDict | New optional key, e.g. `security_report: SecurityReport | None`. |
| **IncidentState.security_passed** | `src/aegis/agent/state.py`, in `IncidentState` | New optional key, e.g. `security_passed: bool | None`. |
| **create_initial_state()** | `src/aegis/agent/state.py` | Extend to set `security_report=None`, `security_passed=None` so all keys exist. |

**Suggested layout:**
- **SecurityFinding / SecurityReport:** `src/aegis/security/models.py` (or `report.py`), then re-export from `src/aegis/security/__init__.py`.
- **IncidentState and create_initial_state:** `src/aegis/agent/state.py`, in the TypedDict definition and in `create_initial_state()`.

---

## 4) Current CLI Output and What to Add

### 4.1 Analyze command and result display

- **Analyze command:** `src/aegis/cli.py`, function `analyze()` (registered with `@typed_command(app)`). It calls `asyncio.run(analyze_incident(...))` and then `_display_analysis_results(console, dict(result))`.
- **Result display:** `src/aegis/cli.py`, function `_display_analysis_results(console, result)`. It renders:
  1. **RCA** — `result.get("rca_result")` in a “Root Cause Analysis” panel.
  2. **Fix proposal** — `result.get("fix_proposal")` in a “Proposed Solution” panel.
  3. **Verification plan** — `result.get("verification_plan")` in a “Verification Plan” panel.

Verification output is therefore “Verification Plan” only (type, duration, analysis steps, scenarios, success criteria). There is no shadow or security result in the CLI today because the CLI does not run shadow.

### 4.2 Where to add a “Security Report” panel

- **File:** `src/aegis/cli.py`
- **Function:** `_display_analysis_results(console, result)`
- **Place:** After the Verification Plan block (after the `verify_panel` / `console.print(verify_panel)` and the following `console.print()`), and before the function ends. Add a conditional block:

```python
# After verification plan panel (existing code):
console.print(verify_panel)
console.print()

# ---- ADD: Security Report panel ----
security_report = result.get("security_report")  # or result.get("security_report")
if security_report is not None:
    # Build text from security_report (passed, summary, findings, etc.)
    sec_lines = [
        f"[bold]Passed:[/bold] {'Yes' if getattr(security_report, 'passed', True) else 'No'}",
        # ... summary, top findings, scanner names ...
    ]
    sec_panel = Panel(
        "\n".join(sec_lines),
        title="[bold magenta]Security Report[/bold magenta]",
        border_style="magenta",
    )
    console.print(sec_panel)
    console.print()
```

- **Exact location:** In `_display_analysis_results()`, after the block that prints `verification_plan` (the `verify_panel` and the subsequent `console.print()`), and before the end of the function. Once `IncidentState` carries `security_report` (and optionally `security_passed`), the CLI will show it as soon as the workflow (or a future “run shadow” step) fills it.

---

## 5) Minimal Implementation Checklist (in order)

Ordered for MVP: Trivy first, then ZAP, then Falco, then runner/orchestrator, then integration.

1. **Trivy**
   - **1.1** Keep `src/aegis/security/trivy.py` as-is (already correct; WSL-friendly).
   - **1.2** Optionally add `scan_config()` or `scan_filesystem()` in the same module if needed later; not required for MVP image gating.

2. **Security data structures**
   - **2.1** Add `SecurityFinding` and `SecurityReport` in `src/aegis/security/models.py` (or equivalent), and export from `src/aegis/security/__init__.py`.
   - **2.2** Add `security_report` and `security_passed` to `IncidentState` and to `create_initial_state()` in `src/aegis/agent/state.py`.

3. **ZAP**
   - **3.1** Add `src/aegis/security/zap.py` with `ZAPScanner` and `baseline_scan(target_url) -> dict` (or `SecurityReport`), using `settings.security.zap_enabled` and `zap_api_url`.
   - **3.2** Use async HTTP (e.g. `httpx`) against ZAP API; no new subprocess helper required for MVP.

4. **Falco**
   - **4.1** Add `src/aegis/security/falco.py` with a small client/helper that checks Falco alerts (or a buffer) for the shadow namespace/time window — e.g. “any High/Critical in last N minutes” → fail.
   - **4.2** Deploy/config of Falco rules (e.g. `deploy/falco/aegis-rules.yaml`) can be a separate task; this step is “code that consumes Falco output” for gating.

5. **Security runner / orchestration**
   - **5.1** Add `src/aegis/security/runner.py` (or similar) with a single entrypoint, e.g. `run_security_checks(env, changes, *, baseline: bool = False) -> SecurityReport`, which:
     - Runs Trivy when `trivy_enabled` and image is present (reuse existing logic from shadow/manager or call `TrivyScanner().scan_image()`).
     - Runs ZAP when `zap_enabled` and a target URL is available (e.g. shadow service URL).
     - Checks Falco when `falco_enabled` for the relevant namespace/window.
   - **5.2** Map runner output into `SecurityReport` and use it in shadow.

6. **Shadow integration**
   - **6.1** **Baseline (A):** In `run_verification()` in `src/aegis/shadow/manager.py`, before `_apply_changes()`, call the security runner for “baseline” (e.g. current image) and store in `env.test_results["baseline_scan"]` (or equivalent).
   - **6.2** **Post-fix (B):** After `_apply_changes()`, keep existing Trivy gate and add ZAP/Falco via the same runner; merge results into `env.test_results` and set `passed = False` if any security check fails.
   - **6.3** **Gating (C):** Leave “block production” logic inside `run_verification()` (and thus already handled by the operator’s use of its return value).

7. **CLI**
   - **7.1** In `_display_analysis_results()` in `src/aegis/cli.py`, add the Security Report panel after the Verification Plan, when `result.get("security_report")` is present.

8. **Operator and state (optional for MVP)**
   - **8.1** If the operator path should persist security results into incident/CR status, extend the structure written by `_run_shadow_verification` (e.g. `_shadow_results[proposal_key]`) to include `security_report` / `security_passed` when available from `shadow_env.test_results`.

---

## Ready to Start

**Current state:**  
`src/aegis/security/trivy.py` is already implemented and wired into shadow for **post-fix image** scans when `"image" in changes`. No new Trivy file is required for MVP.

**First file to add for the security layer:**  
**`src/aegis/security/models.py`** — define `SecurityFinding` and `SecurityReport` here so that:
- Trivy (and later ZAP/Falco) can fill a common structure,
- `IncidentState` and the CLI can use `security_report` / `security_passed` in one place.

After that, the next concrete step is **`src/aegis/security/zap.py`** (ZAP scanner) and then the **security runner** that calls Trivy + ZAP + Falco and produces a `SecurityReport`, followed by wiring that runner into `run_verification()` at the insertion points described in section 2.

---

*Document generated from codebase analysis. No code was modified.*
