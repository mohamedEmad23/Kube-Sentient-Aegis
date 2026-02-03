"""GPU detection helpers."""

from __future__ import annotations

from typing import Any

from kubernetes import client
from kubernetes import config as k8s_config

from aegis.config.settings import settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)

GPU_RESOURCE_KEYS = (
    "nvidia.com/gpu",
    "amd.com/gpu",
)


def detect_gpu_nodes() -> list[str]:
    """Return names of nodes advertising GPU resources."""
    try:
        if settings.kubernetes.in_cluster:
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config(
                config_file=settings.kubernetes.kubeconfig_path,
                context=settings.kubernetes.context,
            )
    except k8s_config.ConfigException as exc:
        log.debug("gpu_kubeconfig_unavailable", error=str(exc))
        return []

    core_api = client.CoreV1Api()
    try:
        nodes = core_api.list_node()
    except client.ApiException as exc:
        log.debug("gpu_node_list_failed", error=exc.reason)
        return []

    gpu_nodes: list[str] = []
    for node in nodes.items:
        allocatable: dict[str, Any] = node.status.allocatable or {}
        if (
            node.metadata
            and node.metadata.name
            and any(
                key in allocatable and allocatable[key] not in ("0", 0) for key in GPU_RESOURCE_KEYS
            )
        ):
            gpu_nodes.append(node.metadata.name)
    return gpu_nodes


def detect_gpu_available() -> bool:
    """Return True if GPU resources are available in the cluster."""
    return bool(detect_gpu_nodes())


__all__ = ["detect_gpu_available", "detect_gpu_nodes"]
