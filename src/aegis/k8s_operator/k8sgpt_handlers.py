"""Kopf handlers for K8sGPT Result CRDs.

This module watches for K8sGPT Result resources created by the K8sGPT operator
and triggers the AEGIS incident response workflow.

K8sGPT Operator detects issues in the cluster and creates Result CRDs.
AEGIS watches these Results and performs:
1. Root Cause Analysis (RCA)
2. Solution Generation
3. Shadow Environment Verification
4. (Optional) Auto-remediation

Usage:
    The handlers are automatically registered when the operator starts.
    They watch the core.k8sgpt.ai/v1alpha1 Result resources.
"""

import asyncio
from typing import Any

import kopf
from kubernetes import client
from kubernetes.client.rest import ApiException

from aegis.crd.k8sgpt_models import (
    K8SGPT_API_GROUP,
    K8SGPT_API_VERSION,
    K8SGPT_RESULT_PLURAL,
    K8sGPTResult,
)
from aegis.observability._logging import get_logger


# HTTP Status Constants
HTTP_409_CONFLICT = 409
HTTP_404_NOT_FOUND = 404

logger = get_logger(__name__)

# In-memory cache of processed results to avoid duplicate processing
_processed_results: set[str] = set()


def _get_result_key(namespace: str, name: str) -> str:
    """Generate a unique key for a Result resource."""
    return f"{namespace}/{name}"


async def _trigger_aegis_workflow(
    result: K8sGPTResult,
    namespace: str,
    logger: kopf.Logger,
) -> dict[str, Any]:
    """Trigger the AEGIS incident response workflow.

    This function orchestrates the AEGIS response to a K8sGPT finding:
    1. Creates an Incident CR (optional, for tracking)
    2. Runs RCA agent
    3. Generates solutions
    4. Optionally verifies in shadow environment

    Args:
        result: The K8sGPT Result that triggered the workflow.
        namespace: The namespace where the issue was detected.
        logger: Kopf logger instance.

    Returns:
        Dictionary with workflow execution results.
    """
    incident_context = result.to_incident_context()

    logger.info(
        f"Starting AEGIS workflow for {result.spec.kind}/{result.spec.name} "
        f"in namespace {namespace}"
    )
    logger.debug(f"Incident context: {incident_context}")

    # Import here to avoid circular imports
    try:
        from aegis.agent.graph import analyze_incident

        # Build K8sGPT analysis data in the expected format for the agent
        # This matches the K8sGPTAnalysis Pydantic model structure
        error_list = [
            {"Text": err.text, "KubernetesDoc": None, "Sensitive": None}
            for err in result.spec.error
            if err.text
        ]
        k8sgpt_data = {
            "status": "OK",
            "problems": len(result.spec.error),
            "results": [
                {
                    "kind": result.spec.kind,
                    "name": result.spec.name,
                    "namespace": namespace,
                    "error": error_list,
                    "parentObject": result.spec.parent_object or None,
                }
            ],
            "errors": None,
            # Include the K8sGPT-generated AI analysis for RCA agent context
            "_k8sgpt_details": result.spec.details,
        }

        # Run the LangGraph workflow
        workflow_result = await analyze_incident(
            resource_type=result.spec.kind,
            resource_name=result.spec.name,
            namespace=namespace,
            k8sgpt_analysis=k8sgpt_data,
        )

        # Extract current_agent safely to avoid union attribute access error
        current_agent_node = workflow_result.get("current_agent")
        current_agent_value = current_agent_node.value if current_agent_node else "unknown"

        return {
            "success": True,
            "workflow_result": {
                "current_agent": current_agent_value,
                "error": workflow_result.get("error"),
                "rca_completed": workflow_result.get("rca_result") is not None,
                "fix_proposed": workflow_result.get("fix_proposal") is not None,
            },
            "message": f"Workflow completed for {result.spec.kind}/{result.spec.name}",
        }

    except ImportError as e:
        logger.warning(f"Agent workflow not available: {e}")
        return {
            "success": False,
            "error": "agent_not_available",
            "message": str(e),
            "incident_context": incident_context,
        }
    except RuntimeError as e:
        logger.exception("Workflow execution failed", exc_info=e)
        return {
            "success": False,
            "error": "workflow_failed",
            "message": str(e),
        }


async def _create_aegis_incident(
    result: K8sGPTResult,
    namespace: str,
    logger: kopf.Logger,
) -> str | None:
    """Create an AEGIS Incident CR to track the response.

    Args:
        result: The K8sGPT Result that triggered the incident.
        namespace: The namespace for the Incident CR.
        logger: Kopf logger instance.

    Returns:
        Name of the created Incident CR, or None if creation failed.
    """
    api = client.CustomObjectsApi()

    incident_name = f"k8sgpt-{result.metadata.name}"

    incident_body = {
        "apiVersion": "aegis.io/v1",
        "kind": "Incident",
        "metadata": {
            "name": incident_name,
            "namespace": namespace,
            "labels": {
                "aegis.io/source": "k8sgpt",
                "aegis.io/resource-kind": result.spec.kind.lower(),
                "aegis.io/resource-name": result.spec.name,
            },
            "annotations": {
                "aegis.io/k8sgpt-result": result.metadata.name,
            },
        },
        "spec": {
            "source": "k8sgpt",
            "resourceRef": {
                "kind": result.spec.kind,
                "name": result.spec.name,
                "namespace": namespace,
            },
            "errors": [err.text for err in result.spec.error if err.text],
            "k8sgptAnalysis": result.spec.details,
            "status": "Detected",
        },
    }

    try:
        api.create_namespaced_custom_object(
            group="aegis.io",
            version="v1",
            namespace=namespace,
            plural="incidents",
            body=incident_body,
        )
        logger.info(f"Created Incident CR: {incident_name}")
    except ApiException as e:
        if e.status == HTTP_409_CONFLICT:
            logger.debug(f"Incident {incident_name} already exists")
            return incident_name
        if e.status == HTTP_404_NOT_FOUND:
            logger.debug("Incident CRD not installed, skipping Incident creation")
            return None
        logger.exception("Failed to create Incident CR", exc_info=e)
        return None
    else:
        return incident_name


@kopf.on.create(K8SGPT_API_GROUP, K8SGPT_API_VERSION, K8SGPT_RESULT_PLURAL)  # type: ignore[misc]
async def handle_k8sgpt_result_create(
    body: kopf.Body,
    _meta: kopf.Meta,
    _spec: kopf.Spec,
    namespace: str,
    name: str,
    logger: kopf.Logger,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle creation of K8sGPT Result resources.

    This is the main entry point for K8sGPT integration.
    When K8sGPT detects an issue, it creates a Result CR.
    This handler picks up that Result and triggers AEGIS workflow.

    Args:
        body: The full Result resource body.
        meta: Resource metadata.
        spec: Resource spec.
        namespace: The namespace of the Result.
        name: The name of the Result.
        logger: Kopf logger instance.
        **kwargs: Additional arguments from kopf.

    Returns:
        Status update for the Result resource.
    """
    result_key = _get_result_key(namespace, name)

    # Check if already processed
    if result_key in _processed_results:
        logger.debug(f"Result {result_key} already processed, skipping")
        return {"processed": True, "skipped": True}

    logger.info(f"K8sGPT Result created: {namespace}/{name}")

    # Parse the Result
    try:
        result = K8sGPTResult.from_kubernetes_object(dict(body))
    except ValueError as e:
        logger.exception("Failed to parse K8sGPT Result", exc_info=e)
        return {"processed": False, "error": str(e)}

    # Log the detected issue
    error_texts = [err.text for err in result.spec.error[:3] if err.text]
    logger.info(
        f"K8sGPT detected issue in {result.spec.kind}/{result.spec.name}: "
        f"{', '.join(error_texts)}..."
    )

    # Create AEGIS Incident for tracking (optional)
    incident_name = await _create_aegis_incident(result, namespace, logger)

    # Trigger the AEGIS workflow
    workflow_result = await _trigger_aegis_workflow(result, namespace, logger)

    # Mark as processed
    _processed_results.add(result_key)

    return {
        "processed": True,
        "incident": incident_name,
        "workflow": workflow_result,
        "message": f"Processed K8sGPT Result for {result.spec.kind}/{result.spec.name}",
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
    """Handle updates to K8sGPT Result resources.

    K8sGPT may update Results if the analysis is refined or if
    the underlying issue changes.

    Args:
        body: The full Result resource body.
        meta: Resource metadata.
        spec: Resource spec.
        namespace: The namespace of the Result.
        name: The name of the Result.
        old: Previous state.
        new: New state.
        diff: Changes between old and new.
        logger: Kopf logger instance.
        **kwargs: Additional arguments from kopf.

    Returns:
        Status update for the Result resource.
    """
    logger.info(f"K8sGPT Result updated: {namespace}/{name}")

    # Check if errors changed
    old_errors = set(old.get("spec", {}).get("error", []))
    new_errors = set(new.get("spec", {}).get("error", []))

    if old_errors == new_errors:
        logger.debug("No change in errors, skipping re-processing")
        return {"processed": True, "skipped": True, "reason": "no_error_change"}

    # Parse the updated Result
    try:
        result = K8sGPTResult.from_kubernetes_object(dict(body))
    except ValueError as e:
        logger.exception("Failed to parse updated K8sGPT Result", exc_info=e)
        return {"processed": False, "error": str(e)}

    # Check for new errors
    new_error_items = new_errors - old_errors
    if new_error_items:
        logger.info(f"New errors detected: {new_error_items}")

        # Remove from processed cache to allow re-processing
        result_key = _get_result_key(namespace, name)
        _processed_results.discard(result_key)

        # Trigger workflow for updated errors
        workflow_result = await _trigger_aegis_workflow(result, namespace, logger)

        _processed_results.add(result_key)

        return {
            "processed": True,
            "new_errors": list(new_error_items),
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
    """Handle deletion of K8sGPT Result resources.

    When a Result is deleted (usually because the issue was resolved),
    we clean up the associated AEGIS Incident if it exists.

    Args:
        body: The full Result resource body.
        meta: Resource metadata.
        namespace: The namespace of the Result.
        name: The name of the Result.
        logger: Kopf logger instance.
        **kwargs: Additional arguments from kopf.
    """
    logger.info(f"K8sGPT Result deleted: {namespace}/{name}")

    # Remove from processed cache
    result_key = _get_result_key(namespace, name)
    _processed_results.discard(result_key)

    # Try to update the associated AEGIS Incident status
    incident_name = f"k8sgpt-{name}"
    api = client.CustomObjectsApi()

    try:
        # Patch the Incident status to "Resolved"
        patch_body = {
            "spec": {
                "status": "Resolved",
                "resolvedAt": asyncio.get_event_loop().time(),
            }
        }

        api.patch_namespaced_custom_object(
            group="aegis.io",
            version="v1",
            namespace=namespace,
            plural="incidents",
            name=incident_name,
            body=patch_body,
        )
        logger.info(f"Marked Incident {incident_name} as resolved")

    except ApiException as e:
        if e.status == HTTP_404_NOT_FOUND:
            logger.debug(f"Incident {incident_name} not found, nothing to update")
        else:
            logger.warning(f"Failed to update Incident status: {e}")


@kopf.on.startup()  # type: ignore[misc]
async def configure_k8sgpt_watching(
    logger: kopf.Logger,
    **_kwargs: Any,
) -> None:
    """Configure K8sGPT Result watching on operator startup.

    This function runs when the operator starts and can be used
    to configure watching behavior or check prerequisites.

    Args:
        logger: Kopf logger instance.
        **_kwargs: Additional arguments from kopf.
    """
    logger.info("Configuring K8sGPT Result watching...")

    # Verify K8sGPT CRD is installed
    api = client.ApiextensionsV1Api()

    try:
        api.read_custom_resource_definition(name=f"{K8SGPT_RESULT_PLURAL}.{K8SGPT_API_GROUP}")
        logger.info("K8sGPT Result CRD is installed")
    except ApiException as e:
        if e.status == HTTP_404_NOT_FOUND:
            logger.warning(
                "K8sGPT Result CRD not found. "
                "Please install K8sGPT operator first: "
                "helm install k8sgpt-operator k8sgpt/k8sgpt-operator"
            )
        else:
            logger.exception("Failed to check K8sGPT CRD", exc_info=e)

    # Clear processed results cache on startup
    _processed_results.clear()
    logger.info("K8sGPT handler initialization complete")
