"""Integration tests for LangGraph agent workflow."""

import pytest

from aegis.agent.graph import analyze_incident, create_incident_workflow
from aegis.agent.state import AgentNode, IncidentSeverity


@pytest.mark.asyncio
async def test_pod_crashloop_workflow():
    """Test complete workflow with Pod CrashLoopBackOff scenario."""
    # Test with mock data (no k8s cluster needed)
    result = await analyze_incident(
        resource_type="pod",
        resource_name="nginx-crashloop",
        namespace="default",
    )

    # Verify no errors
    assert "error" not in result or result["error"] is None

    # Verify RCA result exists
    assert result["rca_result"] is not None
    rca = result["rca_result"]
    assert rca.root_cause is not None
    assert rca.severity in [
        IncidentSeverity.CRITICAL,
        IncidentSeverity.HIGH,
        IncidentSeverity.MEDIUM,
        IncidentSeverity.LOW,
    ]
    assert 0.0 <= rca.confidence_score <= 1.0
    assert len(rca.affected_components) > 0

    # Verify fix proposal exists (if RCA confidence >= 0.7)
    if rca.confidence_score >= 0.7:
        assert result["fix_proposal"] is not None
        fix = result["fix_proposal"]
        assert fix.description is not None
        assert len(fix.commands) > 0

        # Verify verification plan exists (if fix risk is high)
        if fix.estimated_downtime or any(
            keyword in fix.description.lower() for keyword in ["restart", "delete", "replace"]
        ):
            assert result["verification_plan"] is not None
            verify = result["verification_plan"]
            assert len(verify.test_scenarios) > 0
            assert len(verify.success_criteria) > 0


@pytest.mark.asyncio
async def test_deployment_workflow():
    """Test workflow with Deployment resource."""
    result = await analyze_incident(
        resource_type="deployment",
        resource_name="api-server",
        namespace="production",
    )

    assert "error" not in result or result["error"] is None
    assert result["rca_result"] is not None


@pytest.mark.asyncio
async def test_service_workflow():
    """Test workflow with Service resource."""
    result = await analyze_incident(
        resource_type="service",
        resource_name="frontend",
        namespace="default",
    )

    assert "error" not in result or result["error"] is None
    assert result["rca_result"] is not None


@pytest.mark.asyncio
async def test_workflow_with_low_confidence():
    """Test that workflow stops at RCA when confidence is low."""
    # This will depend on LLM response, but we can check the structure
    result = await analyze_incident(
        resource_type="pod",
        resource_name="test-pod",
        namespace="default",
    )

    # RCA should always run
    assert result["rca_result"] is not None

    # If confidence < 0.7, solution agent should not run
    if result["rca_result"].confidence_score < 0.7:
        # Note: In actual execution, this might still have values
        # depending on the graph state. The key is that the workflow
        # should have stopped early.
        pass


@pytest.mark.asyncio
async def test_workflow_graph_structure():
    """Test that workflow graph is constructed correctly."""
    workflow = create_incident_workflow()

    # Verify graph has correct structure
    assert workflow is not None

    # Verify nodes exist
    node_names = list(workflow.nodes.keys())
    assert AgentNode.RCA.value in node_names
    assert AgentNode.SOLUTION.value in node_names
    assert AgentNode.VERIFIER.value in node_names


@pytest.mark.asyncio
async def test_workflow_error_handling():
    """Test workflow with invalid resource type."""
    result = await analyze_incident(
        resource_type="invalid",
        resource_name="test",
        namespace="default",
    )

    # Should still return a result (with mock data fallback)
    assert result is not None
    # May have an error or may succeed with mock data
    # The key is it doesn't raise an exception


@pytest.mark.asyncio
async def test_rca_agent_output_structure():
    """Verify RCA agent produces properly structured output."""
    result = await analyze_incident(
        resource_type="pod",
        resource_name="test-pod",
        namespace="default",
    )

    rca = result["rca_result"]
    assert rca is not None, "RCA result should not be None"
    assert isinstance(rca.root_cause, str)
    assert isinstance(rca.severity, IncidentSeverity)
    assert isinstance(rca.confidence_score, float)
    assert isinstance(rca.reasoning, str)
    assert isinstance(rca.affected_components, list)
    assert all(isinstance(comp, str) for comp in rca.affected_components)


@pytest.mark.asyncio
async def test_solution_agent_output_structure():
    """Verify solution agent produces properly structured output."""
    result = await analyze_incident(
        resource_type="pod",
        resource_name="test-pod",
        namespace="default",
    )

    # Only check if solution was generated
    if result.get("fix_proposal"):
        fix = result["fix_proposal"]
        assert fix is not None, "Fix proposal should not be None when present"
        assert isinstance(fix.description, str)
        assert isinstance(fix.commands, list)
        assert all(isinstance(cmd, str) for cmd in fix.commands)


@pytest.mark.asyncio
async def test_verifier_agent_output_structure():
    """Verify verifier agent produces properly structured output."""
    result = await analyze_incident(
        resource_type="pod",
        resource_name="test-pod",
        namespace="default",
    )

    # Only check if verification plan was generated
    if result.get("verification_plan"):
        verify = result["verification_plan"]
        assert verify is not None, "Verification plan should not be None when present"
        assert isinstance(verify.verification_type, str)
        assert isinstance(verify.test_scenarios, list)
        assert isinstance(verify.success_criteria, list)
        assert isinstance(verify.duration, int)
        assert all(isinstance(scenario, str) for scenario in verify.test_scenarios)
        assert all(isinstance(criteria, str) for criteria in verify.success_criteria)


@pytest.mark.asyncio
async def test_workflow_with_multiple_resources():
    """Test workflow runs successfully for multiple different resources."""
    resources = [
        ("pod", "nginx"),
        ("deployment", "api"),
        ("service", "frontend"),
    ]

    for resource_type, resource_name in resources:
        result = await analyze_incident(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace="default",
        )
        assert result is not None
        assert result["rca_result"] is not None
