"""AEGIS Command Line Interface.

Provides CLI commands for managing the AEGIS operator,
running diagnostics, and interacting with the system.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from aegis.version import __version__

if TYPE_CHECKING:
    from argparse import Namespace


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="aegis",
        description="AEGIS - Autonomous SRE Agent with Shadow Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aegis run                    Start the AEGIS operator
  aegis status                 Check operator status
  aegis diagnose --pod my-pod  Run diagnostics on a pod
  aegis shadow --enable        Enable shadow mode
        """,
    )

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be repeated: -v, -vv, -vvv)",
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Start the AEGIS operator")
    run_parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode with auto-reload",
    )
    run_parser.add_argument(
        "--namespace",
        type=str,
        default=None,
        help="Kubernetes namespace to watch (default: all namespaces)",
    )

    # Status command
    subparsers.add_parser("status", help="Check operator status")

    # Diagnose command
    diagnose_parser = subparsers.add_parser(
        "diagnose", help="Run diagnostics on a resource"
    )
    diagnose_parser.add_argument(
        "--pod",
        type=str,
        help="Pod name to diagnose",
    )
    diagnose_parser.add_argument(
        "--deployment",
        type=str,
        help="Deployment name to diagnose",
    )
    diagnose_parser.add_argument(
        "--namespace",
        "-n",
        type=str,
        default="default",
        help="Kubernetes namespace",
    )

    # Shadow command
    shadow_parser = subparsers.add_parser("shadow", help="Manage shadow mode")
    shadow_group = shadow_parser.add_mutually_exclusive_group(required=True)
    shadow_group.add_argument(
        "--enable",
        action="store_true",
        help="Enable shadow mode",
    )
    shadow_group.add_argument(
        "--disable",
        action="store_true",
        help="Disable shadow mode",
    )
    shadow_group.add_argument(
        "--status",
        action="store_true",
        help="Check shadow mode status",
    )

    # GPU check command
    subparsers.add_parser("gpu-check", help="Check GPU availability for local LLM")

    return parser


def run_operator(args: Namespace) -> int:
    """Start the AEGIS operator."""
    from aegis.operator.main import run

    return run(dev_mode=args.dev, namespace=args.namespace)


def check_status(args: Namespace) -> int:  # noqa: ARG001
    """Check operator status."""
    print("AEGIS Operator Status")
    print("=" * 40)
    print(f"Version: {__version__}")
    print("Status: Not running (use 'aegis run' to start)")
    return 0


def run_diagnose(args: Namespace) -> int:
    """Run diagnostics on a resource."""
    if args.pod:
        print(f"Diagnosing pod: {args.pod} in namespace: {args.namespace}")
    elif args.deployment:
        print(f"Diagnosing deployment: {args.deployment} in namespace: {args.namespace}")
    else:
        print("Error: Specify --pod or --deployment")
        return 1
    return 0


def manage_shadow(args: Namespace) -> int:
    """Manage shadow mode."""
    if args.enable:
        print("Shadow mode enabled")
    elif args.disable:
        print("Shadow mode disabled")
    elif args.status:
        print("Shadow mode: disabled")
    return 0


def check_gpu(args: Namespace) -> int:  # noqa: ARG001
    """Check GPU availability."""
    from aegis.utils.gpu import check_gpu_availability

    return check_gpu_availability()


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    command_handlers = {
        "run": run_operator,
        "status": check_status,
        "diagnose": run_diagnose,
        "shadow": manage_shadow,
        "gpu-check": check_gpu,
    }

    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
