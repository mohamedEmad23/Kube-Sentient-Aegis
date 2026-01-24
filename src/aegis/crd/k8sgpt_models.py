"""Pydantic models for K8sGPT Result Custom Resource.

K8sGPT Operator creates Result CRDs when it detects issues in the cluster.
These models allow AEGIS to parse and process K8sGPT findings.

API Group: core.k8sgpt.ai
API Version: v1alpha1
Kind: Result
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# K8sGPT CRD Constants
K8SGPT_API_GROUP = "core.k8sgpt.ai"
K8SGPT_API_VERSION = "v1alpha1"
K8SGPT_RESULT_PLURAL = "results"
K8SGPT_RESULT_KIND = "Result"


class K8sGPTErrorType(str, Enum):
    """Types of errors K8sGPT can detect."""

    POD_ERROR = "Pod"
    DEPLOYMENT_ERROR = "Deployment"
    REPLICASET_ERROR = "ReplicaSet"
    SERVICE_ERROR = "Service"
    INGRESS_ERROR = "Ingress"
    STATEFULSET_ERROR = "StatefulSet"
    DAEMONSET_ERROR = "DaemonSet"
    CRONJOB_ERROR = "CronJob"
    JOB_ERROR = "Job"
    PVC_ERROR = "PersistentVolumeClaim"
    NODE_ERROR = "Node"
    NETWORK_POLICY_ERROR = "NetworkPolicy"
    HPA_ERROR = "HorizontalPodAutoscaler"
    PDB_ERROR = "PodDisruptionBudget"
    GATEWAY_ERROR = "Gateway"
    HTTPROUTE_ERROR = "HTTPRoute"
    MUTATION_WEBHOOK_ERROR = "MutatingWebhookConfiguration"
    VALIDATION_WEBHOOK_ERROR = "ValidatingWebhookConfiguration"


class K8sGPTSensitiveItem(BaseModel):
    """Sensitive data item that was masked in analysis."""

    unmasked: str = Field(default="", description="Original unmasked value")
    masked: str = Field(default="", description="Masked representation")


class K8sGPTErrorItem(BaseModel):
    """Error item from K8sGPT analysis.

    Based on the CRD schema, each error is an object with:
    - text: The error message
    - sensitive: Optional list of sensitive items
    """

    text: str = Field(default="", description="Error message text")
    sensitive: list[K8sGPTSensitiveItem] = Field(
        default_factory=list, description="Sensitive items in this error"
    )


class K8sGPTResultSpec(BaseModel):
    """Specification for K8sGPT Result CRD.

    Based on the K8sGPT operator Result CRD schema.
    See: https://github.com/k8sgpt-ai/k8sgpt-operator
    """

    backend: str = Field(description="AI backend used for analysis (e.g., localai, openai)")
    kind: str = Field(description="Type of Kubernetes resource analyzed")
    name: str = Field(description="Name of the resource with the issue")
    error: list[K8sGPTErrorItem] = Field(
        default_factory=list,
        description="List of error items detected (each with text and optional sensitive data)",
    )
    details: str = Field(default="", description="AI-generated explanation and recommendations")
    parent_object: str = Field(
        default="",
        alias="parentObject",
        description="Parent object reference (e.g., Deployment for a Pod)",
    )
    sensitive: list[K8sGPTSensitiveItem] = Field(
        default_factory=list, description="List of sensitive items that were masked"
    )

    class Config:
        populate_by_name = True


class K8sGPTResultMetadata(BaseModel):
    """Metadata for K8sGPT Result CRD."""

    name: str = Field(description="Name of the Result resource")
    namespace: str = Field(default="default", description="Namespace")
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    creation_timestamp: datetime | None = Field(default=None, alias="creationTimestamp")
    uid: str | None = Field(default=None)

    class Config:
        populate_by_name = True


class K8sGPTResult(BaseModel):
    """K8sGPT Result Custom Resource Definition.

    This is the main model representing a K8sGPT analysis result.
    K8sGPT operator creates these when it detects issues in the cluster.

    AEGIS watches for these CRDs and triggers its RCA workflow.
    """

    api_version: str = Field(default=f"{K8SGPT_API_GROUP}/{K8SGPT_API_VERSION}", alias="apiVersion")
    kind: str = Field(default=K8SGPT_RESULT_KIND)
    metadata: K8sGPTResultMetadata
    spec: K8sGPTResultSpec

    class Config:
        populate_by_name = True

    def to_incident_context(self) -> dict[str, Any]:
        """Convert K8sGPT Result to AEGIS incident context.

        Returns:
            Dictionary with incident details for AEGIS workflow.
        """
        # Extract error text from error items
        error_texts = [err.text for err in self.spec.error if err.text]

        return {
            "source": "k8sgpt",
            "result_name": self.metadata.name,
            "namespace": self.metadata.namespace,
            "resource_kind": self.spec.kind,
            "resource_name": self.spec.name,
            "errors": error_texts,
            "ai_analysis": self.spec.details,
            "parent_object": self.spec.parent_object,
            "backend": self.spec.backend,
            "detected_at": (
                self.metadata.creation_timestamp.isoformat()
                if self.metadata.creation_timestamp
                else None
            ),
        }

    @classmethod
    def from_kubernetes_object(cls, obj: dict[str, Any]) -> "K8sGPTResult":
        """Create K8sGPTResult from raw Kubernetes API response.

        Args:
            obj: Raw dictionary from Kubernetes API.

        Returns:
            K8sGPTResult instance.
        """
        metadata_dict = obj.get("metadata", {})
        metadata = K8sGPTResultMetadata(
            name=metadata_dict.get("name", ""),
            namespace=metadata_dict.get("namespace", "default"),
            labels=metadata_dict.get("labels", {}),
            annotations=metadata_dict.get("annotations", {}),
            uid=metadata_dict.get("uid"),
        )
        # Set creation_timestamp separately if present
        if "creationTimestamp" in metadata_dict:
            metadata.creation_timestamp = metadata_dict["creationTimestamp"]

        spec_data = obj.get("spec", {})

        # Parse error field - handle both object format and legacy string format
        raw_errors = spec_data.get("error", [])
        parsed_errors: list[K8sGPTErrorItem] = []
        for err in raw_errors:
            if isinstance(err, dict):
                # New format: {text: "...", sensitive: [...]}
                parsed_errors.append(
                    K8sGPTErrorItem(
                        text=err.get("text", ""),
                        sensitive=[K8sGPTSensitiveItem(**s) for s in err.get("sensitive", [])],
                    )
                )
            elif isinstance(err, str):
                # Legacy format: just a string
                parsed_errors.append(K8sGPTErrorItem(text=err))

        spec = K8sGPTResultSpec(
            backend=spec_data.get("backend", "unknown"),
            kind=spec_data.get("kind", ""),
            name=spec_data.get("name", ""),
            error=parsed_errors,
            details=spec_data.get("details", ""),
            sensitive=spec_data.get("sensitive", []),
        )
        # Set parent_object separately if present
        if "parentObject" in spec_data:
            spec.parent_object = spec_data["parentObject"]

        result = cls(
            kind=obj.get("kind", K8SGPT_RESULT_KIND),
            metadata=metadata,
            spec=spec,
        )
        # Set api_version separately if present
        if "apiVersion" in obj:
            result.api_version = obj["apiVersion"]
        return result
