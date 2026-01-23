"""Kubernetes API helpers for collecting resource context."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, cast

import yaml
from kubernetes import client, config  # type: ignore[import-untyped]
from kubernetes.client import ApiException  # type: ignore[import-untyped]

from aegis.config.settings import settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)


DEFAULT_LOG_TAIL_LINES = 200
MAX_LOG_PODS = 3
MAX_EVENTS = 50

_CONFIG_LOCK = Lock()
_CONFIG_LOADED = False
_CONFIG_OK = False


@dataclass(frozen=True)
class K8sResourceContext:
    """Collected Kubernetes context for a resource."""

    logs: str | None
    describe: str | None
    events: str | None


def _request_timeout() -> int:
    return settings.kubernetes.api_timeout


def _load_k8s_config() -> None:
    if settings.kubernetes.in_cluster:
        config.load_incluster_config()
        return
    config.load_kube_config(
        config_file=settings.kubernetes.kubeconfig_path,
        context=settings.kubernetes.context,
    )


def _ensure_k8s_config() -> bool:
    global _CONFIG_LOADED, _CONFIG_OK  # noqa: PLW0603

    with _CONFIG_LOCK:
        if _CONFIG_LOADED:
            return _CONFIG_OK

        try:
            _load_k8s_config()
        except Exception as exc:
            log.warning("k8s_config_load_failed", error=str(exc))
            _CONFIG_OK = False
        else:
            _CONFIG_OK = True

        _CONFIG_LOADED = True
        return _CONFIG_OK


def _resource_kind(resource_type: str) -> str:
    mapping = {
        "pod": "Pod",
        "deployment": "Deployment",
        "service": "Service",
        "statefulset": "StatefulSet",
        "daemonset": "DaemonSet",
        "replicaset": "ReplicaSet",
        "job": "Job",
        "cronjob": "CronJob",
    }
    return mapping.get(resource_type.lower(), resource_type.capitalize())


def _label_selector(match_labels: dict[str, str] | None) -> str | None:
    if not match_labels:
        return None
    parts = [f"{key}={value}" for key, value in match_labels.items()]
    return ",".join(parts)


def _render_resource(obj: Any) -> str:
    data = obj.to_dict()
    metadata = data.get("metadata") or {}
    summary = {
        "apiVersion": data.get("api_version"),
        "kind": data.get("kind"),
        "metadata": {
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "labels": metadata.get("labels"),
            "annotations": metadata.get("annotations"),
        },
        "spec": data.get("spec"),
        "status": data.get("status"),
    }
    return yaml.safe_dump(summary, sort_keys=False, allow_unicode=False)


def _pod_logs(
    core: client.CoreV1Api,
    pod_name: str,
    namespace: str,
    tail_lines: int,
) -> str | None:
    try:
        response = core.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
            timestamps=True,
            _request_timeout=_request_timeout(),
        )
        if response is None:
            return None
        return str(response)
    except ApiException as exc:
        log.warning(
            "k8s_pod_log_failed",
            pod=pod_name,
            namespace=namespace,
            status=exc.status,
            reason=exc.reason,
        )
        return None


def _pod_names_for_resource(
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> list[str]:
    core = client.CoreV1Api()
    apps = client.AppsV1Api()
    rtype = resource_type.lower()

    try:
        if rtype == "deployment":
            deployment = apps.read_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
            selector = deployment.spec.selector.match_labels
        elif rtype == "statefulset":
            statefulset = apps.read_namespaced_stateful_set(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
            selector = statefulset.spec.selector.match_labels
        elif rtype == "daemonset":
            daemonset = apps.read_namespaced_daemon_set(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
            selector = daemonset.spec.selector.match_labels
        elif rtype == "service":
            service = core.read_namespaced_service(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
            selector = service.spec.selector
        else:
            return []
    except ApiException as exc:
        log.warning(
            "k8s_selector_fetch_failed",
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            status=exc.status,
            reason=exc.reason,
        )
        return []

    label_selector = _label_selector(selector)
    if not label_selector:
        return []

    try:
        pod_list = core.list_namespaced_pod(
            namespace=namespace,
            label_selector=label_selector,
            _request_timeout=_request_timeout(),
        )
    except ApiException as exc:
        log.warning(
            "k8s_pod_list_failed",
            namespace=namespace,
            selector=label_selector,
            status=exc.status,
            reason=exc.reason,
        )
        return []

    pod_names = [pod.metadata.name for pod in pod_list.items if pod.metadata and pod.metadata.name]
    return sorted(pod_names)[:MAX_LOG_PODS]


def get_resource_logs(
    resource_type: str,
    resource_name: str,
    namespace: str,
    tail_lines: int = DEFAULT_LOG_TAIL_LINES,
) -> str | None:
    if not _ensure_k8s_config():
        return None

    core = client.CoreV1Api()
    rtype = resource_type.lower()

    if rtype == "pod":
        return _pod_logs(core, resource_name, namespace, tail_lines)

    pod_names = _pod_names_for_resource(resource_type, resource_name, namespace)
    if not pod_names:
        return None

    collected: list[str] = []
    for pod_name in pod_names:
        pod_log = _pod_logs(core, pod_name, namespace, tail_lines)
        if pod_log:
            collected.append(f"== Pod {pod_name} ==\n{pod_log.strip()}")

    if not collected:
        return None

    return "\n\n".join(collected)


def describe_resource(
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> str | None:
    if not _ensure_k8s_config():
        return None

    core = client.CoreV1Api()
    apps = client.AppsV1Api()
    rtype = resource_type.lower()

    try:
        if rtype == "pod":
            obj = core.read_namespaced_pod(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
        elif rtype == "deployment":
            obj = apps.read_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
        elif rtype == "service":
            obj = core.read_namespaced_service(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
        elif rtype == "statefulset":
            obj = apps.read_namespaced_stateful_set(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
        elif rtype == "daemonset":
            obj = apps.read_namespaced_daemon_set(
                name=resource_name,
                namespace=namespace,
                _request_timeout=_request_timeout(),
            )
        else:
            log.warning(
                "k8s_describe_unsupported",
                resource_type=resource_type,
                resource_name=resource_name,
            )
            return None
    except ApiException as exc:
        log.warning(
            "k8s_describe_failed",
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            status=exc.status,
            reason=exc.reason,
        )
        return None

    return _render_resource(obj)


def get_resource_events(
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> str | None:
    if not _ensure_k8s_config():
        return None

    core = client.CoreV1Api()
    kind = _resource_kind(resource_type)
    field_selector = f"involvedObject.kind={kind},involvedObject.name={resource_name}"

    try:
        event_list = core.list_namespaced_event(
            namespace=namespace,
            field_selector=field_selector,
            _request_timeout=_request_timeout(),
        )
    except ApiException as exc:
        log.warning(
            "k8s_event_list_failed",
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            status=exc.status,
            reason=exc.reason,
        )
        return None

    items = event_list.items or []
    if not items:
        return None

    def _event_timestamp(event: client.V1Event) -> datetime:
        return (
            event.last_timestamp
            or event.event_time
            or event.first_timestamp
            or datetime.min
        )

    items.sort(key=_event_timestamp)

    lines: list[str] = []
    for event in items[-MAX_EVENTS:]:
        timestamp = _event_timestamp(event)
        ts = timestamp.isoformat() if timestamp != datetime.min else "unknown-time"
        reason = event.reason or "Unknown"
        event_type = event.type or "Normal"
        count = event.count or 1
        source = ""
        if event.source and event.source.component:
            source = event.source.component
        message = (event.message or "").strip()
        suffix = f" {source}" if source else ""
        lines.append(f"{ts} {event_type} {reason} (x{count}){suffix} {message}".strip())

    return "\n".join(lines)


async def fetch_resource_context(
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> K8sResourceContext:
    """Fetch logs, events, and describe data using the Kubernetes API."""
    results = await asyncio.gather(
        asyncio.to_thread(get_resource_logs, resource_type, resource_name, namespace),
        asyncio.to_thread(describe_resource, resource_type, resource_name, namespace),
        asyncio.to_thread(get_resource_events, resource_type, resource_name, namespace),
        return_exceptions=True,
    )

    def _as_str(result: object, label: str) -> str | None:
        if isinstance(result, BaseException):
            log.warning("k8s_context_unexpected_error", source=label, error=str(result))
            return None
        if result is None:
            return None
        return cast(str, result)

    logs = _as_str(results[0], "logs")
    describe = _as_str(results[1], "describe")
    events = _as_str(results[2], "events")

    return K8sResourceContext(logs=logs, describe=describe, events=events)


__all__ = [
    "K8sResourceContext",
    "describe_resource",
    "fetch_resource_context",
    "get_resource_events",
    "get_resource_logs",
]
