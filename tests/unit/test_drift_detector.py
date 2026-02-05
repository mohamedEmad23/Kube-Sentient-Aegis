"""Unit tests for the Drift Detector.

Tests environment drift detection between production and shadow environments,
including configuration mismatches, RBAC differences, and network policy drift.
"""

from unittest.mock import MagicMock, patch

import pytest
from kubernetes import client

from aegis.shadow.drift_detector import DriftDetector


@pytest.mark.asyncio
async def test_no_drift_identical_deployments():
    """Test no drift detected for identical deployments."""
    detector = DriftDetector()

    # Mock identical deployments
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="app", namespace="test", labels={"app": "test"}),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="app",
                            image="nginx:1.20",
                            resources=client.V1ResourceRequirements(),
                        )
                    ]
                ),
            ),
        ),
    )

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
            mock_api = MagicMock()
            mock_api.list_namespaced_deployment.return_value = client.V1DeploymentList(
                items=[deployment]
            )
            mock_apps.return_value = mock_api

            report = await detector.detect_drift(
                prod_ns="production",
                shadow_ns="shadow-test",
            )

            assert report.drifted is False
            assert report.severity == "none"
            assert len(report.config_mismatches) == 0


@pytest.mark.asyncio
async def test_deployment_replica_drift():
    """Test detects deployment replica mismatch."""
    detector = DriftDetector()

    # Production deployment with 5 replicas
    prod_deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="app", namespace="production"),
        spec=client.V1DeploymentSpec(
            replicas=5,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name="app", image="nginx:1.20")]
                ),
            ),
        ),
    )

    # Shadow deployment with 3 replicas
    shadow_deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="app", namespace="shadow-test"),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name="app", image="nginx:1.20")]
                ),
            ),
        ),
    )

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
            mock_api = MagicMock()

            def list_deployments(namespace, **kwargs):
                if namespace == "production":
                    return client.V1DeploymentList(items=[prod_deployment])
                return client.V1DeploymentList(items=[shadow_deployment])

            mock_api.list_namespaced_deployment.side_effect = list_deployments
            mock_apps.return_value = mock_api

            report = await detector.detect_drift(
                prod_ns="production",
                shadow_ns="shadow-test",
            )

            assert report.drifted is True
            assert report.severity == "high"

            # Check for replica mismatch
            replica_mismatches = [
                m for m in report.config_mismatches if "spec.replicas" in m.get("field", "")
            ]
            assert len(replica_mismatches) > 0

            mismatch = replica_mismatches[0]
            assert mismatch["production_value"] == 5
            assert mismatch["shadow_value"] == 3


@pytest.mark.asyncio
async def test_configmap_data_drift():
    """Test detects ConfigMap data drift."""
    detector = DriftDetector()

    prod_cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name="app-config", namespace="production"),
        data={"LOG_LEVEL": "INFO", "DB_HOST": "prod-db.example.com"},
    )

    shadow_cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name="app-config", namespace="shadow-test"),
        data={"LOG_LEVEL": "DEBUG", "DB_HOST": "prod-db.example.com"},  # Different LOG_LEVEL
    )

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.CoreV1Api") as mock_core:
            with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
                mock_core_api = MagicMock()
                mock_apps_api = MagicMock()

                def list_configmaps(namespace, **kwargs):
                    if namespace == "production":
                        return client.V1ConfigMapList(items=[prod_cm])
                    return client.V1ConfigMapList(items=[shadow_cm])

                mock_core_api.list_namespaced_config_map.side_effect = list_configmaps
                mock_apps_api.list_namespaced_deployment.return_value = client.V1DeploymentList(
                    items=[]
                )

                mock_core.return_value = mock_core_api
                mock_apps.return_value = mock_apps_api

                report = await detector.detect_drift(
                    prod_ns="production",
                    shadow_ns="shadow-test",
                )

                assert report.drifted is True

                # Check for ConfigMap data mismatch
                cm_mismatches = [
                    m
                    for m in report.config_mismatches
                    if "configmap" in m.get("resource_type", "").lower()
                ]
                assert len(cm_mismatches) > 0


@pytest.mark.asyncio
async def test_image_version_drift():
    """Test detects container image version drift."""
    detector = DriftDetector()

    prod_deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="app", namespace="production"),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name="app", image="nginx:1.21")]  # Newer version
                ),
            ),
        ),
    )

    shadow_deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="app", namespace="shadow-test"),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name="app", image="nginx:1.20")]  # Older version
                ),
            ),
        ),
    )

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
            mock_api = MagicMock()

            def list_deployments(namespace, **kwargs):
                if namespace == "production":
                    return client.V1DeploymentList(items=[prod_deployment])
                return client.V1DeploymentList(items=[shadow_deployment])

            mock_api.list_namespaced_deployment.side_effect = list_deployments
            mock_apps.return_value = mock_api

            report = await detector.detect_drift(
                prod_ns="production",
                shadow_ns="shadow-test",
            )

            assert report.drifted is True
            assert report.severity in ["high", "critical"]  # Image drift is critical

            # Check for image mismatch
            image_mismatches = [
                m for m in report.config_mismatches if "image" in m.get("field", "").lower()
            ]
            assert len(image_mismatches) > 0


@pytest.mark.asyncio
async def test_service_port_drift():
    """Test detects Service port configuration drift."""
    detector = DriftDetector()

    prod_service = client.V1Service(
        metadata=client.V1ObjectMeta(name="app-service", namespace="production"),
        spec=client.V1ServiceSpec(
            selector={"app": "test"},
            ports=[
                client.V1ServicePort(name="http", port=80, target_port=8080),
                client.V1ServicePort(name="https", port=443, target_port=8443),
            ],
        ),
    )

    shadow_service = client.V1Service(
        metadata=client.V1ObjectMeta(name="app-service", namespace="shadow-test"),
        spec=client.V1ServiceSpec(
            selector={"app": "test"},
            ports=[
                client.V1ServicePort(name="http", port=80, target_port=8080),
                # Missing HTTPS port
            ],
        ),
    )

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.CoreV1Api") as mock_core:
            with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
                mock_core_api = MagicMock()
                mock_apps_api = MagicMock()

                def list_services(namespace, **kwargs):
                    if namespace == "production":
                        return client.V1ServiceList(items=[prod_service])
                    return client.V1ServiceList(items=[shadow_service])

                mock_core_api.list_namespaced_service.side_effect = list_services
                mock_core_api.list_namespaced_config_map.return_value = client.V1ConfigMapList(
                    items=[]
                )
                mock_apps_api.list_namespaced_deployment.return_value = client.V1DeploymentList(
                    items=[]
                )

                mock_core.return_value = mock_core_api
                mock_apps.return_value = mock_apps_api

                report = await detector.detect_drift(
                    prod_ns="production",
                    shadow_ns="shadow-test",
                )

                assert report.drifted is True

                # Check for service port mismatch
                service_mismatches = [
                    m
                    for m in report.config_mismatches
                    if "service" in m.get("resource_type", "").lower()
                ]
                assert len(service_mismatches) > 0


@pytest.mark.asyncio
async def test_resource_quota_drift():
    """Test detects resource quota differences."""
    detector = DriftDetector()

    prod_quota = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(name="compute-quota", namespace="production"),
        spec=client.V1ResourceQuotaSpec(
            hard={
                "requests.cpu": "10",
                "requests.memory": "20Gi",
                "limits.cpu": "20",
                "limits.memory": "40Gi",
            }
        ),
    )

    shadow_quota = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(name="compute-quota", namespace="shadow-test"),
        spec=client.V1ResourceQuotaSpec(
            hard={
                "requests.cpu": "5",  # Lower quota
                "requests.memory": "10Gi",
                "limits.cpu": "10",
                "limits.memory": "20Gi",
            }
        ),
    )

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.CoreV1Api") as mock_core:
            with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
                mock_core_api = MagicMock()
                mock_apps_api = MagicMock()

                def list_quotas(namespace, **kwargs):
                    if namespace == "production":
                        return client.V1ResourceQuotaList(items=[prod_quota])
                    return client.V1ResourceQuotaList(items=[shadow_quota])

                mock_core_api.list_namespaced_resource_quota.side_effect = list_quotas
                mock_core_api.list_namespaced_service.return_value = client.V1ServiceList(items=[])
                mock_core_api.list_namespaced_config_map.return_value = client.V1ConfigMapList(
                    items=[]
                )
                mock_apps_api.list_namespaced_deployment.return_value = client.V1DeploymentList(
                    items=[]
                )

                mock_core.return_value = mock_core_api
                mock_apps.return_value = mock_apps_api

                report = await detector.detect_drift(
                    prod_ns="production",
                    shadow_ns="shadow-test",
                )

                assert report.drifted is True

                # Check for quota mismatch
                quota_mismatches = [
                    m
                    for m in report.config_mismatches
                    if "quota" in m.get("resource_type", "").lower()
                ]
                assert len(quota_mismatches) > 0


@pytest.mark.asyncio
async def test_drift_severity_calculation():
    """Test drift severity is correctly calculated."""
    detector = DriftDetector()

    # Critical drift: different image versions
    prod_deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="app", namespace="production"),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name="app", image="nginx:2.0")]
                ),
            ),
        ),
    )

    shadow_deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="app", namespace="shadow-test"),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name="app", image="nginx:1.0")]
                ),
            ),
        ),
    )

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
            mock_api = MagicMock()

            def list_deployments(namespace, **kwargs):
                if namespace == "production":
                    return client.V1DeploymentList(items=[prod_deployment])
                return client.V1DeploymentList(items=[shadow_deployment])

            mock_api.list_namespaced_deployment.side_effect = list_deployments
            mock_apps.return_value = mock_api

            report = await detector.detect_drift(
                prod_ns="production",
                shadow_ns="shadow-test",
            )

            assert report.drifted is True
            # Image drift should be high or critical severity
            assert report.severity in ["high", "critical"]


@pytest.mark.asyncio
async def test_drift_detector_empty_namespaces():
    """Test drift detector handles empty namespaces."""
    detector = DriftDetector()

    with patch.object(detector, "_load_k8s_clients"):
        with patch("aegis.shadow.drift_detector.client.CoreV1Api") as mock_core:
            with patch("aegis.shadow.drift_detector.client.AppsV1Api") as mock_apps:
                mock_core_api = MagicMock()
                mock_apps_api = MagicMock()

                # Return empty lists for all resources
                mock_core_api.list_namespaced_service.return_value = client.V1ServiceList(items=[])
                mock_core_api.list_namespaced_config_map.return_value = client.V1ConfigMapList(
                    items=[]
                )
                mock_core_api.list_namespaced_resource_quota.return_value = (
                    client.V1ResourceQuotaList(items=[])
                )
                mock_apps_api.list_namespaced_deployment.return_value = client.V1DeploymentList(
                    items=[]
                )

                mock_core.return_value = mock_core_api
                mock_apps.return_value = mock_apps_api

                report = await detector.detect_drift(
                    prod_ns="production",
                    shadow_ns="shadow-test",
                )

                # Empty namespaces should have no drift
                assert report.drifted is False
                assert report.severity == "none"
                assert len(report.config_mismatches) == 0
