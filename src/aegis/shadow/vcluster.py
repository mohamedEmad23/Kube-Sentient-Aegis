"""vCluster management helpers for shadow environments."""

from __future__ import annotations

import asyncio
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
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return VClusterResult(
            stdout=stdout.decode(errors="replace").strip() if stdout else "",
            stderr=stderr.decode(errors="replace").strip() if stderr else "",
            returncode=process.returncode or 0,
        )

    def create(self, name: str, namespace: str) -> VClusterResult:
        """Create a vCluster without attaching the current kubeconfig."""
        if not self.is_installed():
            raise RuntimeError("vcluster CLI not found on PATH")

        cmd = [self.cli_path or "vcluster", "create", name, "--namespace", namespace]
        if self.template_path and self.template_path.exists():
            cmd.extend(["-f", str(self.template_path)])
        cmd.append("--connect=false")

        result = self._run(cmd)
        if result.returncode != 0 and self.template_path and self.template_path.exists():
            log.warning(
                "vcluster_create_retry_without_template",
                name=name,
                namespace=namespace,
                stderr=result.stderr,
            )
            cmd = [self.cli_path or "vcluster", "create", name, "--namespace", namespace]
            cmd.append("--connect=false")
            result = self._run(cmd)
        if result.returncode != 0:
            log.error(
                "vcluster_create_failed",
                name=name,
                namespace=namespace,
                stderr=result.stderr,
            )
            raise RuntimeError(f"vcluster create failed: {result.stderr or 'unknown error'}")

        log.info(
            "vcluster_created",
            name=name,
            namespace=namespace,
        )
        return result

    def get_kubeconfig(self, name: str, namespace: str) -> str:
        """Get kubeconfig for a vCluster via `vcluster connect --print`."""
        if not self.is_installed():
            raise RuntimeError("vcluster CLI not found on PATH")

        cmd = [
            self.cli_path or "vcluster",
            "connect",
            name,
            "--namespace",
            namespace,
            "--print",
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
        return result.stdout

    def delete(self, name: str, namespace: str) -> VClusterResult:
        """Delete a vCluster (best-effort)."""
        if not self.is_installed():
            raise RuntimeError("vcluster CLI not found on PATH")

        cmd = [self.cli_path or "vcluster", "delete", name, "--namespace", namespace]
        result = self._run(cmd)
        if result.returncode != 0:
            log.warning(
                "vcluster_delete_failed",
                name=name,
                namespace=namespace,
                stderr=result.stderr,
            )
        else:
            log.info(
                "vcluster_deleted",
                name=name,
                namespace=namespace,
            )
        return result


__all__ = ["VClusterManager", "VClusterResult"]
