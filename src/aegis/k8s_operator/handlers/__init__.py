<<<<<<< HEAD
"""AEGIS Operator Handlers.

Kopf-based event handlers for Kubernetes resources:
- incident.py: Pod/Deployment incident detection and remediation
- shadow.py: Shadow environment verification daemons
- index.py: In-memory resource indexing for fast lookups
- k8sgpt_handlers: K8sGPT Result CRD watching and processing

All handlers are automatically registered when this module is imported.
The main operator (main.py) will invoke kopf.run() which discovers
and activates all decorated handlers.
"""

# Import all handler modules to register their decorators
# These modules contain @kopf.on.* decorated functions that
# are automatically registered in kopf's global registry
# Import K8sGPT Result handlers from parent module
from aegis.k8s_operator import k8sgpt_handlers
from aegis.k8s_operator.handlers import incident, index, shadow


# Export for explicit imports if needed
__all__ = [
    "incident",
    "index",
    "k8sgpt_handlers",
    "shadow",
]
=======
"""AEGIS Operator Handlers.

Kopf-based event handlers for Kubernetes resources:
- incident.py: Pod/Deployment incident detection and remediation
- shadow.py: Shadow environment verification daemons
- index.py: In-memory resource indexing for fast lookups
- approval.py: Human-in-the-loop approval workflow handlers
- k8sgpt_handlers: K8sGPT Result CRD watching and processing

All handlers are automatically registered when this module is imported.
The main operator (main.py) will invoke kopf.run() which discovers
and activates all decorated handlers.
"""

# Import all handler modules to register their decorators
# These modules contain @kopf.on.* decorated functions that
# are automatically registered in kopf's global registry
# Import K8sGPT Result handlers from parent module
from aegis.k8s_operator import k8sgpt_handlers
from aegis.k8s_operator.handlers import approval, incident, index, shadow


# Export for explicit imports if needed
__all__ = [
    "approval",
    "incident",
    "index",
    "k8sgpt_handlers",
    "shadow",
]
>>>>>>> af4493e9664b4940d61757df392615e5aaeb514e
