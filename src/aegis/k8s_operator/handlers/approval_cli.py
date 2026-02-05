"""Terminal-based Production Approval CLI.

Implements interactive yes/no prompts for human-in-the-loop approval
before deploying fixes to production. Used by shadow verification workflow.
"""

from typing import Any

from aegis.agent.state import FixProposal
from aegis.observability._logging import get_logger


log = get_logger(__name__)


def request_production_approval_cli(
    *,
    incident_id: str,
    fix_proposal: FixProposal,
    shadow_results: dict[str, Any],
    namespace: str,
    resource_name: str,
    resource_type: str,
) -> bool:
    """Request human approval for production deployment via terminal prompt.

    Displays shadow verification results and blocks until user responds
    with 'yes' or 'no' via stdin.

    Args:
        incident_id: Unique incident ID
        fix_proposal: Proposed fix from solution agent
        shadow_results: Results from shadow verification
        namespace: Kubernetes namespace
        resource_name: Resource name
        resource_type: Resource type

    Returns:
        True if approved (user typed 'yes'), False otherwise
    """
    # Check production lock status
    try:
        from aegis.incident import get_incident_queue

        queue = get_incident_queue()
        locked, lock_reason = queue.is_production_locked()

        if locked:
            print("\n" + "=" * 80)
            print("⛔ PRODUCTION DEPLOYMENT BLOCKED")
            print("=" * 80)
            print()
            print(f"Production is currently locked: {lock_reason}")
            print()
            print("Please resolve the blocking incident before proceeding.")
            print("To unlock manually, use: aegis queue unlock --force")
            print()
            print("=" * 80)
            print()

            log.warning(
                "production_deployment_blocked_by_lock",
                incident_id=incident_id,
                lock_reason=lock_reason,
            )
            return False
    except Exception as e:
        log.warning("production_lock_check_failed", error=str(e))
        # Continue with approval prompt despite error

    # Verify security scan passed
    security_results = shadow_results.get("security", {})
    if security_results and not security_results.get("passed", True):
        critical_vulns = security_results.get("critical_vulnerabilities", [])
        if critical_vulns:
            print("\n" + "=" * 80)
            print("⛔ SECURITY GATE BLOCKED - CRITICAL VULNERABILITIES DETECTED")
            print("=" * 80)
            print()
            print(f"Found {len(critical_vulns)} Critical vulnerability(ies):")
            for vuln in critical_vulns[:3]:  # Show top 3
                severity = vuln.get("severity", "UNKNOWN")
                cve_id = vuln.get("id", "N/A")
                description = vuln.get("description", "No description")
                print(f"  [{severity}] {cve_id}: {description}")
            print()
            print("Deployment rejected due to security policy.")
            print("=" * 80)
            print()

            log.error(
                "production_deployment_blocked_by_security",
                incident_id=incident_id,
                critical_vulns=len(critical_vulns),
            )
            return False

    # Build approval summary
    print("\n" + "=" * 80)
    print("SHADOW VERIFICATION COMPLETED - PRODUCTION APPROVAL REQUIRED")
    print("=" * 80)
    print()

    print(f"Incident ID: {incident_id}")
    print(f"Resource: {resource_type}/{resource_name}")
    print(f"Namespace: {namespace}")
    print()

    print("FIX PROPOSAL:")
    print(f"  Type: {fix_proposal.fix_type.value}")
    print(f"  Description: {fix_proposal.description}")
    print(f"  Confidence: {fix_proposal.confidence_score:.1%}")
    print()

    if fix_proposal.estimated_downtime:
        print(f"  Estimated Downtime: {fix_proposal.estimated_downtime}")

    if fix_proposal.risks:
        print("  Risks:")
        for risk in fix_proposal.risks:
            print(f"    - {risk}")
        print()

    # Shadow verification results
    print("SHADOW VERIFICATION RESULTS:")

    if security_results:
        security_passed = security_results.get("passed", False)
        status_symbol = "✓" if security_passed else "✗"
        print(f"  {status_symbol} Security Scans: {'PASSED' if security_passed else 'FAILED'}")

        if not security_passed and security_results.get("errors"):
            for error in security_results["errors"]:
                print(f"      ERROR: {error}")

    smoke_tests = shadow_results.get("smoke_tests", {})
    if smoke_tests:
        passed = smoke_tests.get("passed_tests", 0)
        total = smoke_tests.get("total_tests", 0)
        status_symbol = "✓" if passed == total else "✗"
        print(f"  {status_symbol} Smoke Tests: PASSED ({passed}/{total})")

    load_tests = shadow_results.get("load_tests", {})
    if load_tests:
        success = load_tests.get("success", False)
        p99_latency = load_tests.get("p99_latency_ms")
        status_symbol = "✓" if success else "✗"
        print(f"  {status_symbol} Load Tests: {'PASSED' if success else 'FAILED'}", end="")
        if p99_latency:
            print(f" (p99: {p99_latency:.0f}ms)")
        else:
            print()

    drift_report = shadow_results.get("drift_report", {})
    if drift_report:
        drifted = drift_report.get("drifted", False)
        severity = drift_report.get("severity", "none")
        if drifted:
            print(f"  ⚠ Environment Drift: {severity.upper()} severity")
            mismatches = drift_report.get("config_mismatches", [])
            if mismatches:
                print(f"      {len(mismatches)} configuration mismatches detected")

    print()
    print("=" * 80)
    print()

    # Approval prompt
    while True:
        try:
            response = input("Apply fix to production? [yes/no]: ").strip().lower()

            if response in ["yes", "y"]:
                log.info(
                    "production_deployment_approved",
                    incident_id=incident_id,
                    resource=f"{resource_type}/{resource_name}",
                )
                print()
                print("✓ Deployment approved. Applying fix to production...")
                print()
                return True
            if response in ["no", "n"]:
                log.info(
                    "production_deployment_rejected",
                    incident_id=incident_id,
                    resource=f"{resource_type}/{resource_name}",
                )
                print()
                print("✗ Deployment rejected. Generating incident report...")
                print()
                return False
            print("Invalid response. Please type 'yes' or 'no'.")
        except (EOFError, KeyboardInterrupt):
            print("\n\n✗ Approval interrupted. Deployment cancelled.")
            log.warning("approval_interrupted", incident_id=incident_id)
            return False


def generate_incident_report(
    *,
    incident_id: str,
    fix_proposal: FixProposal,
    shadow_results: dict[str, Any],
    namespace: str,
    resource_name: str,
    resource_type: str,
    rca_summary: str | None = None,
) -> str:
    """Generate human-readable incident report when deployment is rejected.

    Args:
        incident_id: Unique incident ID
        fix_proposal: Proposed fix
        shadow_results: Shadow verification results
        namespace: Kubernetes namespace
        resource_name: Resource name
        resource_type: Resource type
        rca_summary: Optional RCA summary

    Returns:
        Formatted report string
    """
    report_lines = [
        "=" * 80,
        "INCIDENT REPORT (PRODUCTION DEPLOYMENT REJECTED)",
        "=" * 80,
        "",
        f"Incident ID: {incident_id}",
        f"Resource: {resource_type}/{resource_name}",
        f"Namespace: {namespace}",
        f"Generated: {shadow_results.get('timestamp', 'N/A')}",
        "",
        "-" * 80,
        "ROOT CAUSE ANALYSIS",
        "-" * 80,
    ]

    if rca_summary:
        report_lines.append(rca_summary)
    else:
        report_lines.append("(RCA summary not available)")

    report_lines.extend(
        [
            "",
            "-" * 80,
            "PROPOSED FIX (NOT APPLIED)",
            "-" * 80,
            f"Type: {fix_proposal.fix_type.value}",
            f"Description: {fix_proposal.description}",
            f"Confidence: {fix_proposal.confidence_score:.1%}",
            "",
        ]
    )

    if fix_proposal.commands:
        report_lines.append("Commands:")
        for cmd in fix_proposal.commands:
            report_lines.append(f"  $ {cmd}")
        report_lines.append("")

    report_lines.extend(
        [
            "-" * 80,
            "SHADOW VERIFICATION RESULTS",
            "-" * 80,
        ]
    )

    for key, value in shadow_results.items():
        report_lines.append(f"{key}: {value}")

    report_lines.extend(
        [
            "",
            "-" * 80,
            "RECOMMENDED ACTIONS",
            "-" * 80,
            "1. Review shadow verification results above",
            "2. Manually investigate production cluster",
            "3. If fix is valid, apply commands manually with caution",
            "4. Monitor metrics post-deployment",
            "",
            "=" * 80,
        ]
    )

    return "\n".join(report_lines)


__all__ = [
    "generate_incident_report",
    "request_production_approval_cli",
]
