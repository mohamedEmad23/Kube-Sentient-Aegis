"""vCluster management helpers for shadow environments."""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from aegis.observability._logging import get_logger
from aegis.shadow.errors import ShadowWorkflowError


log = get_logger(__name__)


@dataclass(frozen=True)
class VClusterResult:
    """Result of a vCluster CLI invocation."""

    stdout: str
    stderr: str
    returncode: int


class VClusterManager:
    """Thin wrapper around the vCluster CLI."""

    def __init__(
        self,
        template_path: Path | None = None,
        *,
        kubeconfig_path: str | Path | None = None,
        context: str | None = None,
    ) -> None:
        self.template_path = Path(template_path) if template_path else None
        self.kubeconfig_path = self._normalize_kubeconfig_path(kubeconfig_path)
        self.context = context.strip() if context and context.strip() else None
        self.cli_path = shutil.which("vcluster")

    def is_installed(self) -> bool:
        """Check if vcluster binary is available."""
        return self.cli_path is not None

    @staticmethod
    def _normalize_kubeconfig_path(value: str | Path | None) -> str | None:
        """Normalize kubeconfig path values from settings/env vars."""
        if not value:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        expanded = Path(os.path.expandvars(raw)).expanduser()
        normalized = str(expanded).strip()
        return normalized or None

    def _apply_global_flags(self, cmd: list[str]) -> list[str]:
        """Apply global vcluster CLI flags for deterministic cluster selection."""
        command = list(cmd)
        if self.context:
            command.extend(["--context", self.context])
        return command

    def _run(self, args: list[str]) -> VClusterResult:
        """Run vcluster command and return result."""
        return asyncio.run(self._run_async(args))

    async def _run_async(self, args: list[str]) -> VClusterResult:
        """Run vcluster command asynchronously and return result."""
        # Pass current environment to subprocess to ensure KUBECONFIG is inherited
        env = os.environ.copy()
        if self.kubeconfig_path:
            env["KUBECONFIG"] = self.kubeconfig_path

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await process.communicate()
        return VClusterResult(
            stdout=stdout.decode(errors="replace").strip() if stdout else "",
            stderr=stderr.decode(errors="replace").strip() if stderr else "",
            returncode=process.returncode or 0,
        )

    def create(self, name: str, namespace: str) -> VClusterResult:
        """Create a vCluster with external exposure for operator access."""
        if not self.is_installed():
            raise ShadowWorkflowError(
                code="vcluster_cli_missing",
                phase="vcluster_create",
                message="vcluster CLI not found on PATH",
                retryable=False,
            )

        # 2026 Fix: Use --expose to create a LoadBalancer/NodePort
        # This allows the operator (external to cluster) to reach the vCluster API
        cmd = [
            self.cli_path or "vcluster",
            "create",
            name,
            "--namespace",
            namespace,
            "--expose",
        ]

        if self.template_path and self.template_path.exists():
            cmd.extend(["-f", str(self.template_path)])

        # We handle connection manually via 'connect --print'
        cmd.append("--connect=false")
        cmd = self._apply_global_flags(cmd)

        log.info(f"Creating vCluster: {' '.join(cmd)}")
        result = self._run(cmd)

        if result.returncode != 0:
            log.error(
                "vcluster_create_failed",
                name=name,
                namespace=namespace,
                stderr=result.stderr,
            )
            raise ShadowWorkflowError(
                code="vcluster_create_failed",
                phase="vcluster_create",
                message=f"vcluster create failed: {result.stderr or 'unknown error'}",
                retryable=True,
                details={
                    "shadow_id": name,
                    "namespace": namespace,
                    "returncode": result.returncode,
                    "kubeconfig_path": self.kubeconfig_path,
                    "context": self.context,
                },
            )

        return result

    def get_kubeconfig(self, name: str, namespace: str) -> str:
        """Get kubeconfig for a vCluster via `vcluster connect --print`."""
        if not self.is_installed():
            raise ShadowWorkflowError(
                code="vcluster_cli_missing",
                phase="vcluster_get_kubeconfig",
                message="vcluster CLI not found on PATH",
                retryable=False,
            )

        # 2026 Fix: explicitly use the external host provided by --expose
        # The --server argument is often not needed if --expose set up the LB correctly,
        # but we must ensure we don't get a localhost config.
        cmd = [
            self.cli_path or "vcluster",
            "connect",
            name,
            "--namespace",
            namespace,
            "--print",
            "--silent",  # Suppress logs in stdout, we only want the yaml
        ]
        cmd = self._apply_global_flags(cmd)
        result = self._run(cmd)
        if result.returncode != 0:
            log.error(
                "vcluster_kubeconfig_failed",
                name=name,
                namespace=namespace,
                stderr=result.stderr,
            )
            raise ShadowWorkflowError(
                code="vcluster_connect_failed",
                phase="vcluster_get_kubeconfig",
                message=f"vcluster connect --print failed: {result.stderr or 'unknown error'}",
                retryable=True,
                details={
                    "shadow_id": name,
                    "namespace": namespace,
                    "returncode": result.returncode,
                    "kubeconfig_path": self.kubeconfig_path,
                    "context": self.context,
                },
            )

        if not result.stdout:
            raise ShadowWorkflowError(
                code="vcluster_kubeconfig_empty",
                phase="vcluster_get_kubeconfig",
                message="vcluster connect returned empty kubeconfig output",
                retryable=True,
                details={"shadow_id": name, "namespace": namespace},
            )

        # Post-processing: If running in Docker and vCluster returns 127.0.0.1
        # (common with port-forwarding logic), we might need to patch it.
        # However, --expose should return the LB IP.
        return result.stdout

    def delete(self, name: str, namespace: str) -> VClusterResult:
        if not self.is_installed():
            raise ShadowWorkflowError(
                code="vcluster_cli_missing",
                phase="vcluster_delete",
                message="vcluster CLI not found on PATH",
                retryable=False,
            )

        cmd = [self.cli_path or "vcluster", "delete", name, "--namespace", namespace]
        cmd = self._apply_global_flags(cmd)
        result = self._run(cmd)
        if result.returncode != 0:
            raise ShadowWorkflowError(
                code="vcluster_delete_failed",
                phase="vcluster_delete",
                message=f"vcluster delete failed: {result.stderr or 'unknown error'}",
                retryable=True,
                details={
                    "shadow_id": name,
                    "namespace": namespace,
                    "returncode": result.returncode,
                    "kubeconfig_path": self.kubeconfig_path,
                    "context": self.context,
                },
            )
        return result


__all__ = ["VClusterManager", "VClusterResult"]
