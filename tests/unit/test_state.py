"""Test agent state models."""

from datetime import UTC, datetime

import pytest

from aegis.agent.state import (
    FixProposal,
    FixType,
    IncidentSeverity,
    LoadTestConfig,
    RCAResult,
    VerificationPlan,
)


def test_rca_result_verbose_fields() -> None:
    """Test RCAResult has verbose output fields."""
    rca = RCAResult(
        root_cause="Test cause",
        analysis_steps=["step1", "step2"],
        evidence_summary=["evidence1"],
        decision_rationale="Test rationale",
        severity=IncidentSeverity.HIGH,
        confidence_score=0.9,
        reasoning="Test reasoning",
        timestamp=datetime.now(tz=UTC),
    )
    assert len(rca.analysis_steps) == 2
    assert len(rca.evidence_summary) == 1
    assert rca.decision_rationale == "Test rationale"
    assert rca.root_cause == "Test cause"


def test_rca_result_defaults() -> None:
    """Test RCAResult default values for verbose fields."""
    rca = RCAResult(
        root_cause="Test",
        severity=IncidentSeverity.MEDIUM,
        confidence_score=0.8,
        reasoning="Test",
        timestamp=datetime.now(tz=UTC),
    )
    # Should have empty defaults
    assert isinstance(rca.analysis_steps, list)
    assert isinstance(rca.evidence_summary, list)
    assert isinstance(rca.decision_rationale, str)


def test_fix_proposal_verbose_fields() -> None:
    """Test FixProposal has verbose output fields."""
    fix = FixProposal(
        fix_type=FixType.CONFIG_CHANGE,
        description="Test fix",
        analysis_steps=["step1"],
        decision_rationale="Test rationale",
        commands=["kubectl patch"],
        confidence_score=0.8,
    )
    assert len(fix.analysis_steps) == 1
    assert fix.decision_rationale == "Test rationale"
    assert fix.fix_type == FixType.CONFIG_CHANGE


def test_verification_plan_verbose_fields() -> None:
    """Test VerificationPlan has verbose output fields."""
    plan = VerificationPlan(
        verification_type="shadow",
        analysis_steps=["step1"],
        decision_rationale="Test rationale",
        test_scenarios=["health"],
        success_criteria=["no errors"],
        duration=60,
        load_test_config=LoadTestConfig(
            users=1, spawn_rate=1, duration_seconds=10, target_url="http://test"
        ),
        security_checks=[],
    )
    assert len(plan.analysis_steps) == 1
    assert plan.decision_rationale == "Test rationale"
    assert plan.security_checks == []
    assert plan.verification_type == "shadow"


def test_load_test_config_validation() -> None:
    """Test LoadTestConfig field validation."""
    # Valid config
    config = LoadTestConfig(users=10, spawn_rate=1, duration_seconds=60, target_url="http://test")
    assert config.users == 10
    assert config.spawn_rate == 1

    # Invalid users (must be >= 1)
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        LoadTestConfig(users=0, spawn_rate=1, duration_seconds=10, target_url="http://test")

    # Invalid spawn_rate (must be >= 1)
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        LoadTestConfig(users=1, spawn_rate=0, duration_seconds=10, target_url="http://test")

    # Invalid duration (must be >= 10)
    with pytest.raises(ValueError, match="greater than or equal to 10"):
        LoadTestConfig(users=1, spawn_rate=1, duration_seconds=5, target_url="http://test")


def test_fix_type_enum() -> None:
    """Test FixType enum values."""
    assert FixType.CONFIG_CHANGE.value == "config_change"
    assert FixType.RESTART.value == "restart"
    assert FixType.SCALE.value == "scale"
    assert FixType.ROLLBACK.value == "rollback"


def test_incident_severity_enum() -> None:
    """Test IncidentSeverity enum values."""
    assert IncidentSeverity.CRITICAL.value == "critical"
    assert IncidentSeverity.HIGH.value == "high"
    assert IncidentSeverity.MEDIUM.value == "medium"
    assert IncidentSeverity.LOW.value == "low"
