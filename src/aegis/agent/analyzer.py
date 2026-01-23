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

        # if self.is_available:
        #     log.info("k8sgpt_found", path=self.cli_path)
        # else:
        #     log.warning(
        #         "k8sgpt_not_found",
        #         message="K8sGPT CLI not installed. Will use mock data for development.",
        #         install_instructions="brew install k8sgpt OR visit https://github.com/k8sgpt-ai/k8sgpt",
        #     )

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
                # return self._get_mock_analysis(resource_type, resource_name, namespace)
                raise RuntimeError("K8sGPT analysis timed out")

            if process.returncode != 0:
                log.error(
                    "k8sgpt_execution_failed",
                    returncode=process.returncode,
                    stderr=stderr.decode(),
                )
                # Fallback to mock on error
                # return self._get_mock_analysis(resource_type, resource_name, namespace)
                raise RuntimeError("K8sGPT execution failed")

            # Parse JSON output
            raw_output = json.loads(stdout.decode())

            # Filter results for specific resource
            # K8sGPT returns name as "namespace/resource" so we need to match both formats
            results_list = raw_output.get("results") or []

            # Debug: log what K8sGPT returned
            # log.info(
            #     "k8sgpt_raw_results",
            #     total_results=len(results_list),
            #     result_names=[r.get("name") for r in results_list],
            #     looking_for=[resource_name, f"{namespace}/{resource_name}"],
            # )

            filtered_results = [
                r for r in results_list
                if r.get("name") == resource_name
                or r.get("name") == f"{namespace}/{resource_name}"
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

            # log.info(
            #     "k8sgpt_analysis_completed",
            #     resource=f"{resource_type}/{resource_name}",
            #     problems=analysis.problems,
            # )

        except json.JSONDecodeError as e:
            log.exception("k8sgpt_json_parse_error", error=str(e))
            # return self._get_mock_analysis(resource_type, resource_name, namespace)
            raise RuntimeError("K8sGPT JSON parse error")

        except OSError as e:
            log.exception("k8sgpt_unexpected_error", error=str(e))
            # return self._get_mock_analysis(resource_type, resource_name, namespace)
            raise RuntimeError("K8sGPT unexpected error")
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
                                f"Pod {resource_name} is in CrashLoopBackOff state. "
                                "Container 'app' is failing with exit code 1. "
                                "Last termination reason: Error. "
                                "Check logs for application-specific errors."
                            ),
                            "kubernetes_doc": "https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-states",
                        }
                    ],
                    "parent_object": None,
                }
            ]

        elif resource_type.lower() == "deployment":
            mock_data["results"] = [
                {
                    "kind": "Deployment",
                    "name": resource_name,
                    "namespace": namespace,
                    "error": [
                        {
                            "text": (
                                f"Deployment {resource_name} has 0/3 replicas available. "
                                "ImagePullBackOff error detected. "
                                "Container image 'nginx:invalid-tag' not found. "
                                "Verify image name and tag."
                            ),
                            "kubernetes_doc": "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/",
                        }
                    ],
                    "parent_object": None,
                }
            ]

        elif resource_type.lower() == "service":
            mock_data["results"] = [
                {
                    "kind": "Service",
                    "name": resource_name,
                    "namespace": namespace,
                    "error": [
                        {
                            "text": (
                                f"Service {resource_name} has no endpoints. "
                                "No pods match the selector labels. "
                                "Check that pod labels match service selector."
                            ),
                            "kubernetes_doc": "https://kubernetes.io/docs/concepts/services-networking/service/",
                        }
                    ],
                    "parent_object": None,
                }
            ]

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
