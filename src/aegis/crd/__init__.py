"""AEGIS Custom Resource Definition Models.

This module provides Pydantic models for parsing and working with
Kubernetes Custom Resource Definitions used by AEGIS.

Supported CRDs:
- K8sGPT Result (core.k8sgpt.ai/v1alpha1)
- AEGIS Incident (aegis.io/v1)
"""

from aegis.crd.incident_models import (
    AEGIS_API_GROUP,
    AEGIS_API_VERSION,
    AEGIS_INCIDENT_KIND,
    AEGIS_INCIDENT_PLURAL,
    AegisIncident,
    Approval,
    ApprovalStatus,
    FixProposal,
    FixType,
    IncidentCondition,
    IncidentMetadata,
    IncidentPhase,
    IncidentSeverity,
    IncidentSource,
    IncidentSpec,
    IncidentStatus,
    MonitoringStatus,
    RCAResult,
    ResourceRef,
    ShadowVerification,
)
from aegis.crd.k8sgpt_models import (
    K8SGPT_API_GROUP,
    K8SGPT_API_VERSION,
    K8SGPT_RESULT_KIND,
    K8SGPT_RESULT_PLURAL,
    K8sGPTErrorItem,
    K8sGPTErrorType,
    K8sGPTResult,
    K8sGPTResultMetadata,
    K8sGPTResultSpec,
    K8sGPTSensitiveItem,
)


__all__ = [
    "AEGIS_API_GROUP",
    "AEGIS_API_VERSION",
    "AEGIS_INCIDENT_KIND",
    "AEGIS_INCIDENT_PLURAL",
    "K8SGPT_API_GROUP",
    "K8SGPT_API_VERSION",
    "K8SGPT_RESULT_KIND",
    "K8SGPT_RESULT_PLURAL",
    "AegisIncident",
    "Approval",
    "ApprovalStatus",
    "FixProposal",
    "FixType",
    "IncidentCondition",
    "IncidentMetadata",
    "IncidentPhase",
    "IncidentSeverity",
    "IncidentSource",
    "IncidentSpec",
    "IncidentStatus",
    "K8sGPTErrorItem",
    "K8sGPTErrorType",
    "K8sGPTResult",
    "K8sGPTResultMetadata",
    "K8sGPTResultSpec",
    "K8sGPTSensitiveItem",
    "MonitoringStatus",
    "RCAResult",
    "ResourceRef",
    "ShadowVerification",
]
