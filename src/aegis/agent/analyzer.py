"""K8sGPT analyzer with graceful fallback for development.

Provides a production-ready wrapper for K8sGPT CLI tool with:
- Automatic detection of K8sGPT availability
- Mock data support for development without clusters
- Async subprocess execution
- JSON output parsing with Pydantic validation
- Comprehensive error handling and logging
"""

import asyncio
import json
import shutil
from typing import Any

from aegis.agent.state import K8sGPTAnalysis
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import k8sgpt_analyses_total


log = get_logger(__name__)


class K8sGPTAnalyzer:
    """Wrapper for K8sGPT CLI with mock support for development."""

    def __init__(self) -> None:
        """Initialize K8sGPT analyzer and check availability."""
        self.cli_path = shutil.which("k8sgpt")
        self.backend = "localai"  # K8sGPT backend name (not the model name)
        self.is_available = self.cli_path is not None

    async def analyze(
        self,
        resource_type: str,
        resource_name: str,
        namespace: str = "default",
        explain: bool = True,
        use_mock: bool = False,
    ) -> K8sGPTAnalysis:
        """Run K8sGPT analysis on a Kubernetes resource.

        Args:
            resource_type: Type of resource (Pod, Deployment, Service, etc.)
            resource_name: Name of the resource to analyze
            namespace: Kubernetes namespace (default: "default")
            explain: Whether to use AI to explain issues (default: True)
            use_mock: Force use of mock data even if K8sGPT is available

        Returns:
            K8sGPTAnalysis: Parsed analysis results

        Raises:
            RuntimeError: If K8sGPT execution fails

        Example:
            >>> analyzer = K8sGPTAnalyzer()
            >>> result = await analyzer.analyze("Pod", "nginx-crashloop")
            >>> print(result.problems)
            1
        """
        # Use mock data if K8sGPT not available or explicitly requested
        if use_mock or not self.is_available:
            log.info(
                "using_mock_data",
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
            )
            return self._get_mock_analysis(resource_type, resource_name, namespace)

        # Build K8sGPT command
        # K8sGPT filters are case-sensitive (e.g., "Pod" not "pod")
        filter_name = resource_type.capitalize()
        cmd: list[str] = [
            self.cli_path or "",
            "analyze",
            f"--filter={filter_name}",
            f"--namespace={namespace}",
            "--output=json",
        ]

        if explain:
            cmd.append("--explain")
            cmd.extend([f"--backend={self.backend}"])

        log.debug(
            "running_k8sgpt",
            command=" ".join(cmd),
            resource=f"{resource_type}/{resource_name}",
        )

        try:
            # Execute K8sGPT CLI asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=settings.kubernetes.api_timeout,
                )
            except TimeoutError:
                log.exception("k8sgpt_timeout", timeout=settings.kubernetes.api_timeout)
                process.kill()
                await process.wait()
                return self._get_mock_analysis(resource_type, resource_name, namespace)

            if process.returncode != 0:
                log.error(
                    "k8sgpt_execution_failed",
                    returncode=process.returncode,
                    stderr=stderr.decode(),
                )
                # Fallback to mock on error
                return self._get_mock_analysis(resource_type, resource_name, namespace)

            # Parse JSON output
            raw_output = json.loads(stdout.decode())

            # Filter results for specific resource
            # K8sGPT returns name as "namespace/resource" so we need to match both formats
            results_list = raw_output.get("results") or []

            filtered_results = [
                r
                for r in results_list
                if r.get("name") == resource_name or r.get("name") == f"{namespace}/{resource_name}"
            ]

            filtered_output = {
                "status": raw_output.get("status", "OK"),
                "problems": len(filtered_results),
                "results": filtered_results,
                "errors": raw_output.get("errors"),
            }

            # Validate and parse with Pydantic
            analysis = K8sGPTAnalysis.model_validate(filtered_output)

            # Record metrics
            k8sgpt_analyses_total.labels(
                resource_type=resource_type,
                problems_found=str(analysis.problems),
            ).inc()

        except json.JSONDecodeError as e:
            log.exception("k8sgpt_json_parse_error", error=str(e))
            return self._get_mock_analysis(resource_type, resource_name, namespace)

        except OSError as e:
            log.exception("k8sgpt_unexpected_error", error=str(e))
            return self._get_mock_analysis(resource_type, resource_name, namespace)
        else:
            return analysis

    def _get_mock_analysis(
        self,
        resource_type: str,
        resource_name: str,
        namespace: str,
    ) -> K8sGPTAnalysis:
        """Generate mock K8sGPT analysis for development.

        Args:
            resource_type: Type of resource
            resource_name: Name of the resource
            namespace: Kubernetes namespace

        Returns:
            K8sGPTAnalysis: Mock analysis data
        """
        # Mock data based on resource type
        mock_data: dict[str, Any] = {
            "status": "OK",
            "problems": 1,
            "results": [],
            "errors": None,
        }

        if resource_type.lower() == "pod":
            mock_data["results"] = [
                {
                    "kind": "Pod",
                    "name": resource_name,
                    "namespace": namespace,
                    "error": [
                        {
                            "text": (
                                f"CRITICAL: Pod {resource_name} is in CrashLoopBackOff state with 5 restart attempts. "
                                "Container 'app' is failing with exit code 1 due to missing DATABASE_URL environment variable. "
                                "Application logs show: 'Error: DATABASE_URL environment variable is required'. "
                                "Last termination reason: Error. Restart policy: Always. Container must be reconfigured "
                                "with the correct environment variable to resolve this issue."
                            ),
                            "kubernetes_doc": "https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-states",
                        }
                    ],
                    "parent_object": None,
                }
            ]
            # Store mock kubectl context for this resource type
            mock_data["_mock_kubectl"] = {
                "logs": (
                    "2026-01-24T02:15:00Z Starting application...\n"
                    "2026-01-24T02:15:01Z Loading configuration...\n"
                    "2026-01-24T02:15:01Z ERROR: DATABASE_URL environment variable is required\n"
                    "2026-01-24T02:15:01Z Application failed to start\n"
                    "2026-01-24T02:15:01Z Exit code: 1"
                ),
                "describe": (
                    f"Name:         {resource_name}\n"
                    f"Namespace:    {namespace}\n"
                    f"Status:       Running\n"
                    f"IP:           10.244.0.5\n"
                    f"Containers:\n"
                    f"  app:\n"
                    f"    Image:          nginx:latest\n"
                    f"    State:          Waiting\n"
                    f"      Reason:       CrashLoopBackOff\n"
                    f"    Last State:     Terminated\n"
                    f"      Reason:       Error\n"
                    f"      Exit Code:    1\n"
                    f"    Ready:          False\n"
                    f"    Restart Count:  5\n"
                    f"    Environment:\n"
                    f"      APP_ENV:      production\n"
                    f"      # DATABASE_URL is MISSING\n"
                    f"Conditions:\n"
                    f"  Type              Status\n"
                    f"  Initialized       True\n"
                    f"  Ready             False\n"
                    f"  ContainersReady   False\n"
                    f"  PodScheduled      True\n"
                    f"Events:\n"
                    f"  Type     Reason     Message\n"
                    f"  Normal   Scheduled  Successfully assigned {namespace}/{resource_name} to node-1\n"
                    f"  Normal   Pulled     Container image pulled successfully\n"
                    f"  Warning  BackOff    Back-off restarting failed container"
                ),
                "events": (
                    f"LAST SEEN   TYPE      REASON     OBJECT                MESSAGE\n"
                    f"2m          Normal    Scheduled  pod/{resource_name}   Successfully assigned to node-1\n"
                    f"2m          Normal    Pulling    pod/{resource_name}   Pulling image nginx:latest\n"
                    f"2m          Normal    Pulled     pod/{resource_name}   Successfully pulled image\n"
                    f"1m          Warning   BackOff    pod/{resource_name}   Back-off restarting failed container\n"
                    f"30s         Warning   BackOff    pod/{resource_name}   Back-off 40s restarting failed container"
                ),
            }

        elif resource_type.lower() == "deployment":
            mock_data["results"] = [
                {
                    "kind": "Deployment",
                    "name": resource_name,
                    "namespace": namespace,
                    "error": [
                        {
                            "text": (
                                f"CRITICAL: Deployment {resource_name} has 0/3 replicas available. "
                                "ImagePullBackOff error detected for all pods. "
                                "Container image 'nginx:invalid-tag-v999' not found in registry. "
                                "Image pull failed with: 'manifest unknown: manifest unknown'. "
                                "Verify the image name and tag exist in the container registry."
                            ),
                            "kubernetes_doc": "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/",
                        }
                    ],
                    "parent_object": None,
                }
            ]
            mock_data["_mock_kubectl"] = {
                "logs": "Error from server: container not ready",
                "describe": (
                    f"Name:               {resource_name}\n"
                    f"Namespace:          {namespace}\n"
                    f"Replicas:           3 desired | 3 updated | 3 total | 0 available\n"
                    f"Conditions:\n"
                    f"  Type           Status  Reason\n"
                    f"  Available      False   MinimumReplicasUnavailable\n"
                    f"  Progressing    False   ProgressDeadlineExceeded\n"
                    f"Pod Template:\n"
                    f"  Containers:\n"
                    f"   app:\n"
                    f"    Image:        nginx:invalid-tag-v999\n"
                    f"Events:\n"
                    f"  Type     Reason             Message\n"
                    f"  Warning  FailedCreate       Error creating pod: ImagePullBackOff"
                ),
                "events": (
                    f"LAST SEEN   TYPE      REASON          OBJECT                    MESSAGE\n"
                    f"5m          Normal    ScalingReplicaSet   deployment/{resource_name}   Scaled up replica set\n"
                    f"5m          Warning   FailedCreate        replicaset/{resource_name}   ImagePullBackOff\n"
                    f"3m          Warning   Failed              pod/{resource_name}-xxx      Failed to pull image"
                ),
            }

        elif resource_type.lower() == "service":
            mock_data["results"] = [
                {
                    "kind": "Service",
                    "name": resource_name,
                    "namespace": namespace,
                    "error": [
                        {
                            "text": (
                                f"WARNING: Service {resource_name} has no endpoints. "
                                "Service selector 'app=myapp' does not match any pod labels. "
                                "Pods in namespace have labels 'app=my-app' (hyphenated). "
                                "Fix the service selector to match pod labels."
                            ),
                            "kubernetes_doc": "https://kubernetes.io/docs/concepts/services-networking/service/",
                        }
                    ],
                    "parent_object": None,
                }
            ]
            mock_data["_mock_kubectl"] = {
                "logs": "N/A - Service resource",
                "describe": (
                    f"Name:              {resource_name}\n"
                    f"Namespace:         {namespace}\n"
                    f"Type:              ClusterIP\n"
                    f"IP:                10.96.123.45\n"
                    f"Port:              http  80/TCP\n"
                    f"TargetPort:        8080/TCP\n"
                    f"Endpoints:         <none>\n"
                    f"Selector:          app=myapp\n"
                    f"Session Affinity:  None\n"
                    f"Events:            <none>"
                ),
                "events": (
                    f"LAST SEEN   TYPE      REASON     OBJECT                 MESSAGE\n"
                    f"10m         Normal    Created    service/{resource_name}   Service created"
                ),
            }

        else:
            # Generic mock for other resource types
            mock_data["results"] = [
                {
                    "kind": resource_type,
                    "name": resource_name,
                    "namespace": namespace,
                    "error": [
                        {
                            "text": f"{resource_type} {resource_name} has configuration issues. Mock data for development.",
                            "kubernetes_doc": "https://kubernetes.io/docs/home/",
                        }
                    ],
                    "parent_object": None,
                }
            ]
            mock_data["_mock_kubectl"] = {
                "logs": "Mock logs for development",
                "describe": f"Mock describe for {resource_type}/{resource_name}",
                "events": "No events",
            }

        return K8sGPTAnalysis.model_validate(mock_data)

    async def check_installation(self) -> dict[str, Any]:
        """Check K8sGPT installation and configuration.

        Returns:
            dict: Installation status with details
        """
        status: dict[str, Any] = {
            "installed": self.is_available,
            "cli_path": self.cli_path,
            "backend_configured": False,
            "version": None,
        }

        if self.is_available and self.cli_path:
            try:
                # Get version
                process = await asyncio.create_subprocess_exec(
                    self.cli_path,
                    "version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
                if process.returncode == 0:
                    status["version"] = stdout.decode().strip()

                # Check if backend is configured
                process = await asyncio.create_subprocess_exec(
                    self.cli_path,
                    "auth",
                    "list",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
                if process.returncode == 0 and self.backend in stdout.decode():
                    status["backend_configured"] = True

            except (OSError, TimeoutError) as e:
                log.warning("k8sgpt_check_failed", error=str(e))

        return status


# Module-level cache
_analyzer_cache: K8sGPTAnalyzer | None = None


def get_k8sgpt_analyzer() -> K8sGPTAnalyzer:
    """Get or create K8sGPT analyzer instance.

    Returns:
        K8sGPTAnalyzer: Cached analyzer instance
    """
    global _analyzer_cache  # noqa: PLW0603
    if _analyzer_cache is None:
        _analyzer_cache = K8sGPTAnalyzer()
    return _analyzer_cache


__all__ = ["K8sGPTAnalyzer", "get_k8sgpt_analyzer"]
