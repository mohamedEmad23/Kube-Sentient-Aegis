# Skill: Kubernetes Operator Development with Kopf

## Metadata
- **Domain**: Kubernetes, Python, Operators
- **Tools**: kopf, kubernetes-client, pydantic
- **Complexity**: Advanced
- **Autonomy**: Semi-Autonomous (requires approval for cluster changes)

## Capability Statement
Expert in building production-grade Kubernetes operators using kopf framework. Creates operators with proper error handling, status management, and idempotent reconciliation loops.

## Core Competencies

### 1. Operator Scaffolding
```python
# Generate operator structure with:
# - Event handlers (create, update, delete, resume)
# - Status subresource management
# - Admission webhooks
# - Multi-resource coordination
```

### 2. Kopf Best Practices
- **Idempotency**: Ensure handlers can run multiple times safely
- **Atomicity**: Use strategic merge patches, not full replacements
- **State Management**: Track reconciliation state in status subresource
- **Error Handling**: Implement exponential backoff with `@kopf.on.error`
- **Finalizers**: Clean up external resources on deletion
- **Timers**: Use `@kopf.timer` for periodic reconciliation

### 3. CRD Design Patterns
```yaml
# OpenAPI v3 schema validation
# Immutable fields enforcement
# Default values and field validation
# Status conditions following K8s conventions
```

### 4. Testing Strategy
- Unit tests with `pytest` and `kopf.testing`
- Integration tests with `kind` clusters
- Chaos testing with deliberate API failures
- Performance testing under high resource churn

## Execution Protocol

### Pre-Development Checklist
- [ ] Fetch latest kopf documentation via context7 MCP
- [ ] Review Kubernetes API conventions
- [ ] Verify Python 3.12+ compatibility
- [ ] Check existing CRD definitions in cluster

### Development Workflow
1. **Design Phase**
   - Define CRD schema with comprehensive validation
   - Map resource lifecycle to operator handlers
   - Identify external dependencies (ConfigMaps, Secrets, etc.)

2. **Implementation Phase**
   - Scaffold operator with uv project structure
   - Implement handlers with explicit logging
   - Add Prometheus metrics via `kopf.on.event`
   - Create Dockerfile with minimal base image

3. **Testing Phase**
   - Run operator locally with `kopf run`
   - Test in kind cluster with sample CRs
   - Verify garbage collection and finalizers
   - Load test with 100+ resources

4. **Deployment Phase**
   - Generate RBAC manifests (ServiceAccount, Role, RoleBinding)
   - Create Deployment with proper resource limits
   - Configure leader election for HA
   - Set up monitoring and alerting

## Code Generation Standards

### Handler Template
```python
import kopf
import kubernetes.client as k8s_client
from pydantic import BaseModel, ValidationError

class SpecModel(BaseModel):
    replicas: int
    image: str

@kopf.on.create('example.com', 'v1', 'myresources')
def create_handler(spec, name, namespace, logger, **kwargs):
    """Idempotent create handler with validation."""
    try:
        validated = SpecModel(**spec)
    except ValidationError as e:
        raise kopf.PermanentError(f"Invalid spec: {e}")

    logger.info(f"Creating resource {name} in {namespace}")
    # Implementation with strategic merge patch
    return {'status': 'created'}
```

### Status Management
```python
@kopf.on.field('example.com', 'v1', 'myresources', field='spec.replicas')
def replicas_changed(old, new, status, patch, logger, **kwargs):
    """React to spec changes and update status."""
    patch.status['observedReplicas'] = new
    patch.status['conditions'] = [{
        'type': 'Ready',
        'status': 'True',
        'reason': 'ReplicasUpdated'
    }]
```

## Integration Points

### With k8sGPT
- Emit structured logs for k8sGPT analysis
- Add annotations for diagnostic context
- Use standard K8s event naming

### With MCP Context7
- Auto-fetch kopf API reference before coding
- Query for operator design patterns
- Validate against K8s API conventions

### With vLLM/Ollama
- Use operators to manage model deployments
- Handle GPU resource allocation
- Implement canary rollouts for models

## Common Pitfalls to Avoid

❌ **Don't**: Use `kubectl apply` in handlers (race conditions)
✅ **Do**: Use strategic merge patch via Python client

❌ **Don't**: Store state in operator memory
✅ **Do**: Persist state in resource status subresource

❌ **Don't**: Handle all events synchronously
✅ **Do**: Use timers for expensive operations

❌ **Don't**: Ignore event deduplication
✅ **Do**: Check resource generation/UID before acting

## Security Considerations
- Minimal RBAC permissions (principle of least privilege)
- Validate all user input in CRD spec
- Never log sensitive data (secrets, tokens)
- Use Pod Security Standards (restricted profile)
- Implement admission webhooks for mutation/validation

## Performance Optimization
- Use informer caching to reduce API calls
- Batch operations when possible
- Implement rate limiting for external APIs
- Profile with cProfile for handler bottlenecks
- Set appropriate resource limits in Deployment

## Output Artifacts
When invoking this skill, generate:
1. **Operator Code** (`operator.py`) - Main handler logic
2. **CRD Manifest** (`crd.yaml`) - Custom Resource Definition
3. **RBAC** (`rbac.yaml`) - ServiceAccount, Role, RoleBinding
4. **Deployment** (`deployment.yaml`) - Operator deployment
5. **Dockerfile** - Multi-stage build with uv
6. **Tests** (`test_operator.py`) - Pytest suite
7. **Makefile** - Targets for build, test, deploy

## Verification Checklist
- [ ] Operator handles create/update/delete events
- [ ] Status subresource reflects actual state
- [ ] Finalizers clean up external resources
- [ ] All tests pass with 80%+ coverage
- [ ] RBAC follows least privilege
- [ ] Dockerfile passes security scan
- [ ] Operator recovers from API server restarts
- [ ] Metrics exposed on /metrics endpoint
