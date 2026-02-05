"""vCluster management helpers for shadow environments."""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from aegis.observability._logging import get_logger


log = get_logger(__name__)


@dataclass(frozen=True)
class VClusterResult:
    """Result of a vCluster CLI invocation."""

    stdout: str
    stderr: str
    returncode: int


class VClusterManager:
    """Thin wrapper around the vCluster CLI."""

    def __init__(self, template_path: Path | None = None) -> None:
        self.template_path = Path(template_path) if template_path else None
        self.cli_path = shutil.which("vcluster")

    def is_installed(self) -> bool:
        """Check if vcluster binary is available."""
        return self.cli_path is not None

    def _run(self, args: list[str]) -> VClusterResult:
        """Run vcluster command and return result."""
        return asyncio.run(self._run_async(args))

    async def _run_async(self, args: list[str]) -> VClusterResult:
        """Run vcluster command asynchronously and return result."""
        # Pass current environment to subprocess to ensure KUBECONFIG is inherited
        env = os.environ.copy()

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
            raise RuntimeError("vcluster CLI not found on PATH")

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

        log.info(f"Creating vCluster: {' '.join(cmd)}")
        result = self._run(cmd)

        if result.returncode != 0:
            log.error(
                "vcluster_create_failed",
                name=name,
                namespace=namespace,
                stderr=result.stderr,
            )
            raise RuntimeError(f"vcluster create failed: {result.stderr or 'unknown error'}")

        return result

    def get_kubeconfig(self, name: str, namespace: str) -> str:
        """Get kubeconfig for a vCluster via `vcluster connect --print`."""
        if not self.is_installed():
            raise RuntimeError("vcluster CLI not found on PATH")

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
        result = self._run(cmd)
        if result.returncode != 0:
            log.error(
                "vcluster_kubeconfig_failed",
                name=name,
                namespace=namespace,
                stderr=result.stderr,
            )
            raise RuntimeError(
                f"vcluster connect --print failed: {result.stderr or 'unknown error'}"
            )

        if not result.stdout:
            raise RuntimeError("vcluster connect returned empty kubeconfig output")

        # Post-processing: If running in Docker and vCluster returns 127.0.0.1
        # (common with port-forwarding logic), we might need to patch it.
        # However, --expose should return the LB IP.
        return result.stdout

    def delete(self, name: str, namespace: str) -> VClusterResult:
        if not self.is_installed():
            raise RuntimeError("vcluster CLI not found on PATH")

        cmd = [self.cli_path or "vcluster", "delete", name, "--namespace", namespace]
        result = self._run(cmd)
        return result


__all__ = ["VClusterManager", "VClusterResult"]
