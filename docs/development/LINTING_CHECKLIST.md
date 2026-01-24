# Linting & Type Checking Checklist

## Summary
- **Total Ruff Errors**: 106 remaining
- **Mypy Errors**: 14 type errors
- **Detect-Secrets**: 3 false positives (need allowlist)
- **Other Hooks**: ✅ PASSED

---

## 1. DETECT-SECRETS ISSUES (3 entries - False Positives)

These are template values, not actual secrets. Fix by adding pragma comments.

### ❌ deploy/k8sgpt/k8sgpt-cr.yaml:103
- **Issue**: "secret" keyword detected (false positive - template variable)
- **Fix**: Add `# pragma: allowlist secret` comment

### ❌ deploy/k8sgpt/k8sgpt-values.yaml:36
- **Issue**: "secret" keyword detected (false positive)
- **Fix**: Add `# pragma: allowlist secret` comment

### ❌ deploy/k8sgpt/k8sgpt-values.yaml:37
- **Issue**: "secret" keyword detected (false positive)
- **Fix**: Add `# pragma: allowlist secret` comment

---

## 2. RUFF LINTING ISSUES (106 errors)

### By File:

#### deploy/k8sgpt/k8sgpt_handler.py: 18 issues
- [ ] **ERA001** (2): Remove commented-out code at lines 91-92
- [ ] **TRY300** (1): Line 160 - Consider moving statement to else block
- [ ] **PLR2004** (2): Magic values 409, 404 at lines 162, 165
- [ ] **ARG001** (3): Unused args - meta(175), kwargs(180)

#### src/aegis/agent/agents/solution_agent.py: 9 issues
- [ ] **ERA001** (9): Remove commented-out log statements at lines 94-99, 114-119

#### src/aegis/agent/agents/verifier_agent.py: 1 issue
- [ ] **ERA001** (1): Remove commented-out code

#### src/aegis/agent/analyzer.py: 12 issues
- [ ] **ERA001** (8): Remove commented-out k8sgpt logs
- [ ] **SIM108** (1): Line 81 - Use ternary operator

#### src/aegis/agent/graph.py: 7 issues
- [ ] **ERA001** (4): Remove commented-out logs
- [ ] **SIM108** (1): Line 81 - Use ternary operator + fix args

#### src/aegis/agent/llm/ollama.py: 22 issues
- [ ] **ERA001** (20): Remove commented-out logging statements (lines 38-43, 103-109, 124-130, 240-245, 259-263)
- [ ] **TRY300** (1): Line 133 - Move return to else block
- [ ] **TRY400** (1): Use logging.exception instead of error

#### src/aegis/cli.py: 28 issues
- [ ] **ARG001** (3): Unused args - auto_fix(252), namespace(409), severity(415)
- [ ] **ERA001** (8): Remove commented logs
- [ ] **F841** (2): Unused variables - fix_proposal(347), verification_plan(348)
- [ ] **TRY301** (1): Line 355 - Abstract raise
- [ ] **PLC0415** (5): Move imports to top level (656, 658, 671, 697, 698, 729)
- [ ] **PLR2004** (2): Magic values 404(722), 200(732)
- [ ] **BLE001** (2): Don't catch blind Exception (740, 754)

#### src/aegis/config/settings.py: 1 issue
- [ ] **ERA001** (1): Line 333 - Remove commented default value

#### src/aegis/k8s_operator/handlers/shadow.py: 4 issues
- [ ] **TRY300** (1): Line 441 - Move return to else
- [ ] **BLE001** (1): Line 443 - Specific exception instead of Exception
- [ ] **TRY400** (1): Line 444 - Use logging.exception instead of error

#### src/aegis/k8s_operator/k8sgpt_handlers.py: 26 issues
- [ ] **BLE001** (4): Don't catch blind Exception (131, 249, 323)
- [ ] **TRY400** (4): Use logging.exception instead of error (132, 205, 250, 324, 435)
- [ ] **TRY300** (1): Line 196 - Move return to else
- [ ] **PLR2004** (4): Magic values 409(199), 404(202, 402, 428)
- [ ] **ARG001** (9): Unused arguments (meta x3, spec x3, body(352), kwargs x2, settings(410), diff(286))

#### src/aegis/shadow/manager.py: 10 issues
- [ ] **TRY400** (3): Use logging.exception instead of error (174, 237, 261)
- [ ] **TRY300** (1): Line 232 - Move return to else
- [ ] **BLE001** (2): Don't catch blind Exception (234, 260)
- [ ] **PLR2004** (4): Magic values 0.8(217), 409(291), 404(299)
- [ ] **PLW0603** (1): Line 439 - Global statement discouraged

---

## 3. MYPY TYPE CHECKING ISSUES (14 errors)

### ❌ src/aegis/crd/k8sgpt_models.py
- [ ] Line 127: Missing type parameters for generic type "dict" → Use `dict[str, Any]`
- [ ] Line 154: Missing type parameters for generic type "dict" → Use `dict[str, Any]`

### ❌ src/aegis/shadow/manager.py
- [ ] Line 21-22: Missing stubs for "kubernetes" import (can add to mypy ignore)

### ❌ src/aegis/k8s_operator/k8sgpt_handlers.py
- [ ] Line 22-23: Missing stubs for "kubernetes" (can add to mypy ignore)
- [ ] Line 113: Union type has no attribute "value"
- [ ] Lines 209+: Untyped decorators (kopf handlers) - needs `# type: ignore`

### ❌ src/aegis/cli.py
- [ ] Line 676: Missing type parameters for generic dict
- [ ] Line 697: Missing stubs for "kubernetes"
- [ ] Line 729: Missing stubs for "httpx"

---

## 4. PRE-COMMIT HOOKS STATUS

- ✅ **ruff-format**: PASSED
- ✅ **bandit**: PASSED
- ✅ **shellcheck**: PASSED
- ✅ **validate-pyproject.toml**: PASSED
- ❌ **ruff**: 106 errors failing
- ❌ **mypy**: 14 errors failing
- ❌ **detect-secrets**: 3 false positives failing

---

## RESOLUTION PLAN

1. **First**: Fix detect-secrets (add pragma comments)
2. **Second**: Fix mypy issues (type annotations)
3. **Third**: Fix ruff issues (remove comments, refactor code)
4. **Fourth**: Run pre-commit again
5. **Fifth**: Commit with message

---

## Progress

- [ ] Detect-secrets fixed
- [ ] Mypy issues fixed
- [ ] Ruff issues fixed
- [ ] Pre-commit passes
- [ ] Changes committed
