"""
K8sGPT Result Handler for AEGIS Operator

This handler watches for K8sGPT Result CRDs and triggers the AEGIS
incident response workflow when issues are detected.

Integration:
    1. Copy this file to your handlers directory
    2. Import it in your handlers/__init__.py
    3. The Kopf operator will automatically register these handlers

Example handlers/__init__.py:
    from .k8sgpt_handler import (
        handle_k8sgpt_result_create,
        handle_k8sgpt_result_update,
        handle_k8sgpt_result_delete,
    )

Requirements:
    - kopf
    - kubernetes
    - K8sGPT operator installed in cluster
"""

import logging
from typing import Any

import kopf
from kubernetes import client
from kubernetes.client.rest import ApiException


# HTTP Status Constants
HTTP_409_CONFLICT = 409
HTTP_404_NOT_FOUND = 404

# K8sGPT CRD Constants
K8SGPT_API_GROUP = "core.k8sgpt.ai"
K8SGPT_API_VERSION = "v1alpha1"
K8SGPT_RESULT_PLURAL = "results"

# Logger
logger = logging.getLogger(__name__)

# Processed results cache (prevents duplicate processing)
_processed_results: set[str] = set()


def _result_key(namespace: str, name: str) -> str:
    """Generate unique key for a Result."""
    return f"{namespace}/{name}"


async def _trigger_aegis_workflow(
    result_data: dict[str, Any],
    namespace: str,
    log: kopf.Logger,
) -> dict[str, Any]:
    """Trigger the AEGIS RCA workflow for a K8sGPT Result.

    This function should be customized to integrate with your
    specific AEGIS workflow implementation.

    Args:
        result_data: The K8sGPT Result spec data.
        namespace: Namespace where the issue was detected.
        log: Kopf logger.

    Returns:
        Workflow execution result.
    """
    spec = result_data.get("spec", {})

    # Extract incident context
    incident_context = {
        "source": "k8sgpt",
        "resource_kind": spec.get("kind", ""),
        "resource_name": spec.get("name", ""),
        "namespace": namespace,
        "errors": spec.get("error", []),
        "ai_analysis": spec.get("details", ""),
        "parent_object": spec.get("parentObject", ""),
        "backend": spec.get("backend", ""),
    }

    log.info(
        f"AEGIS processing issue: {incident_context['resource_kind']}/"
        f"{incident_context['resource_name']}"
    )
    log.debug(f"Errors: {incident_context['errors']}")
    log.debug(f"AI Analysis: {incident_context['ai_analysis'][:200]}...")

    log.info("Incident context prepared for AEGIS workflow")

    return {
        "success": True,
        "incident_context": incident_context,
        "message": "AEGIS workflow triggered",
    }


async def _create_aegis_incident(
    result_data: dict[str, Any],
    namespace: str,
    log: kopf.Logger,
) -> str | None:
    """Create an AEGIS Incident CR to track the response.

    This is optional - only if you have an Incident CRD defined.

    Args:
        result_data: The K8sGPT Result data.
        namespace: Namespace for the Incident.
        log: Kopf logger.

    Returns:
        Name of created Incident, or None.
    """
    spec = result_data.get("spec", {})
    result_name = result_data.get("metadata", {}).get("name", "unknown")
    incident_name = f"k8sgpt-{result_name}"

    api = client.CustomObjectsApi()

    incident_body = {
        "apiVersion": "aegis.io/v1alpha1",
        "kind": "Incident",
        "metadata": {
            "name": incident_name,
            "namespace": namespace,
            "labels": {
                "aegis.io/source": "k8sgpt",
                "aegis.io/resource-kind": spec.get("kind", "").lower(),
            },
        },
        "spec": {
            "source": "k8sgpt",
            "resourceRef": {
                "kind": spec.get("kind", ""),
                "name": spec.get("name", ""),
                "namespace": namespace,
            },
            "errors": spec.get("error", []),
            "aiAnalysis": spec.get("details", ""),
            "status": "Detected",
        },
    }

    try:
        api.create_namespaced_custom_object(
            group="aegis.io",
            version="v1alpha1",
            namespace=namespace,
            plural="incidents",
            body=incident_body,
        )
        log.info(f"Created Incident: {incident_name}")
    except ApiException as e:
        if e.status == HTTP_409_CONFLICT:
            log.debug(f"Incident {incident_name} already exists")
            return incident_name
        if e.status == HTTP_404_NOT_FOUND:
            log.debug("Incident CRD not installed, skipping")
            return None
        log.warning(f"Failed to create Incident: {e}")
        return None
    else:
        return incident_name


@kopf.on.create(K8SGPT_API_GROUP, K8SGPT_API_VERSION, K8SGPT_RESULT_PLURAL)  # type: ignore[misc]
async def handle_k8sgpt_result_create(
    body: kopf.Body,
    _meta: kopf.Meta,
    spec: kopf.Spec,
    namespace: str,
    name: str,
    logger: kopf.Logger,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle K8sGPT Result creation.

    This handler is triggered when K8sGPT detects an issue and creates
    a Result CRD. It kicks off the AEGIS incident response workflow.
    """
    result_key = _result_key(namespace, name)

    # Avoid duplicate processing
    if result_key in _processed_results:
        logger.debug(f"Result {result_key} already processed")
        return {"processed": True, "skipped": True}

    logger.info(f"K8sGPT Result created: {namespace}/{name}")

    # Log detected issues
    errors = spec.get("error", [])
    resource_kind = spec.get("kind", "Unknown")
    resource_name = spec.get("name", "unknown")

    logger.info(f"K8sGPT detected {len(errors)} issue(s) in {resource_kind}/{resource_name}")
    for i, error in enumerate(errors[:5]):  # Limit to first 5
        logger.info(f"  [{i + 1}] {error}")

    # Create AEGIS Incident (optional)
    incident_name = await _create_aegis_incident(dict(body), namespace, logger)

    # Trigger AEGIS workflow
    workflow_result = await _trigger_aegis_workflow(dict(body), namespace, logger)

    # Mark as processed
    _processed_results.add(result_key)

    return {
        "processed": True,
        "incident": incident_name,
        "workflow": workflow_result,
        "message": f"Processed {resource_kind}/{resource_name}",
    }


@kopf.on.update(K8SGPT_API_GROUP, K8SGPT_API_VERSION, K8SGPT_RESULT_PLURAL)  # type: ignore[misc]
async def handle_k8sgpt_result_update(
    body: kopf.Body,
    _meta: kopf.Meta,
    _spec: kopf.Spec,
    namespace: str,
    name: str,
    old: kopf.BodyEssence,
    new: kopf.BodyEssence,
    _diff: kopf.Diff,
    logger: kopf.Logger,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle K8sGPT Result updates.

    K8sGPT may update Results if analysis is refined or issues change.
    """
    logger.info(f"K8sGPT Result updated: {namespace}/{name}")

    # Check if errors changed
    old_errors = set(old.get("spec", {}).get("error", []))
    new_errors = set(new.get("spec", {}).get("error", []))

    if old_errors == new_errors:
        logger.debug("No change in errors, skipping")
        return {"processed": True, "skipped": True, "reason": "no_error_change"}

    # New errors detected
    added_errors = new_errors - old_errors
    if added_errors:
        logger.info(f"New errors detected: {added_errors}")

        # Remove from cache to allow re-processing
        result_key = _result_key(namespace, name)
        _processed_results.discard(result_key)

        # Re-trigger workflow
        workflow_result = await _trigger_aegis_workflow(dict(body), namespace, logger)

        _processed_results.add(result_key)

        return {
            "processed": True,
            "new_errors": list(added_errors),
            "workflow": workflow_result,
        }

    return {"processed": True, "skipped": True}


@kopf.on.delete(K8SGPT_API_GROUP, K8SGPT_API_VERSION, K8SGPT_RESULT_PLURAL)  # type: ignore[misc]
async def handle_k8sgpt_result_delete(
    _body: kopf.Body,
    _meta: kopf.Meta,
    namespace: str,
    name: str,
    logger: kopf.Logger,
    **_kwargs: Any,
) -> None:
    """Handle K8sGPT Result deletion.

    When a Result is deleted (usually because the issue was resolved),
    we can update the associated AEGIS Incident.
    """
    logger.info(f"K8sGPT Result deleted: {namespace}/{name}")

    # Remove from processed cache
    result_key = _result_key(namespace, name)
    _processed_results.discard(result_key)

    # Try to update AEGIS Incident status
    incident_name = f"k8sgpt-{name}"
    api = client.CustomObjectsApi()

    try:
        patch = {"spec": {"status": "Resolved"}}
        api.patch_namespaced_custom_object(
            group="aegis.io",
            version="v1alpha1",
            namespace=namespace,
            plural="incidents",
            name=incident_name,
            body=patch,
        )
        logger.info(f"Marked Incident {incident_name} as resolved")
    except ApiException as e:
        if e.status != HTTP_404_NOT_FOUND:
            logger.warning(f"Failed to update Incident: {e}")


@kopf.on.startup()  # type: ignore[misc]
async def on_startup(_settings: kopf.OperatorSettings, logger: kopf.Logger, **_: Any) -> None:
    """Configure K8sGPT Result watching on startup."""
    logger.info("Initializing K8sGPT Result watcher...")

    # Verify K8sGPT CRD is installed
    api = client.ApiextensionsV1Api()

    try:
        api.read_custom_resource_definition(name=f"{K8SGPT_RESULT_PLURAL}.{K8SGPT_API_GROUP}")
        logger.info("K8sGPT Result CRD found - watcher enabled")
    except ApiException as e:
        if e.status == HTTP_404_NOT_FOUND:
            logger.warning(
                "K8sGPT Result CRD not found. "
                "Install K8sGPT operator: helm install k8sgpt-operator k8sgpt/k8sgpt-operator"
            )
        else:
            logger.exception("Error checking K8sGPT CRD", exc_info=e)

    # Clear processed cache on startup
    _processed_results.clear()
    logger.info("K8sGPT handler initialized")
