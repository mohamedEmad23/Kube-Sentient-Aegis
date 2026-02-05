"""Unit tests for the incident queue.

Tests priority-based queuing, correlation, deduplication, and production locking.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from aegis.agent.state import IncidentPriority, create_initial_state
from aegis.incident import IncidentQueue


@pytest.mark.asyncio
async def test_priority_ordering():
    """Test that incidents are dequeued in priority order (P0 > P1 > P2 > P3 > P4)."""
    queue = IncidentQueue(max_queue_size=100)

    # Enqueue incidents with mixed priorities
    state_p2 = create_initial_state("Pod", "pod-p2", "default")
    state_p2["priority"] = IncidentPriority.P2
    state_p2["incident_id"] = "inc-1"

    state_p0 = create_initial_state("Pod", "pod-p0", "default")
    state_p0["priority"] = IncidentPriority.P0
    state_p0["incident_id"] = "inc-2"

    state_p1 = create_initial_state("Pod", "pod-p1", "default")
    state_p1["priority"] = IncidentPriority.P1
    state_p1["incident_id"] = "inc-3"

    state_p3 = create_initial_state("Pod", "pod-p3", "default")
    state_p3["priority"] = IncidentPriority.P3
    state_p3["incident_id"] = "inc-4"

    # Enqueue in random order
    await queue.enqueue(state_p2)
    await queue.enqueue(state_p0)
    await queue.enqueue(state_p1)
    await queue.enqueue(state_p3)

    # Dequeue should return P0 first
    incident1 = await queue.dequeue(timeout=1.0)
    assert incident1 is not None
    assert incident1["priority"] == IncidentPriority.P0
    assert incident1["resource_name"] == "pod-p0"

    # Then P1
    incident2 = await queue.dequeue(timeout=1.0)
    assert incident2 is not None
    assert incident2["priority"] == IncidentPriority.P1
    assert incident2["resource_name"] == "pod-p1"

    # Then P2
    incident3 = await queue.dequeue(timeout=1.0)
    assert incident3 is not None
    assert incident3["priority"] == IncidentPriority.P2
    assert incident3["resource_name"] == "pod-p2"

    # Then P3
    incident4 = await queue.dequeue(timeout=1.0)
    assert incident4 is not None
    assert incident4["priority"] == IncidentPriority.P3
    assert incident4["resource_name"] == "pod-p3"


@pytest.mark.asyncio
async def test_incident_correlation():
    """Test that duplicate incidents are correlated within the correlation window."""
    queue = IncidentQueue(correlation_window_seconds=60, max_queue_size=100)

    # Create two incidents for the same resource
    state1 = create_initial_state("Pod", "crashloop-pod", "production")
    state1["priority"] = IncidentPriority.P1
    state1["incident_id"] = "inc-1"

    state2 = create_initial_state("Pod", "crashloop-pod", "production")
    state2["priority"] = IncidentPriority.P1
    state2["incident_id"] = "inc-2"

    # Enqueue first incident
    incident_id_1 = await queue.enqueue(state1)

    # Enqueue duplicate - should be correlated
    duplicate_called = False

    def on_duplicate(correlated_id: str) -> None:
        nonlocal duplicate_called
        duplicate_called = True
        assert correlated_id == incident_id_1

    incident_id_2 = await queue.enqueue(state2, on_duplicate=on_duplicate)

    # Should be correlated to the first incident
    assert duplicate_called is True
    assert incident_id_1 == incident_id_2

    # Dequeue should only return one incident
    incident = await queue.dequeue(timeout=1.0)
    assert incident is not None
    assert incident["resource_name"] == "crashloop-pod"

    # No more incidents
    incident_none = await queue.dequeue(timeout=0.5)
    assert incident_none is None


@pytest.mark.asyncio
async def test_production_lock():
    """Test production deployment locking mechanism."""
    queue = IncidentQueue(max_queue_size=100)

    # Initially unlocked
    locked, reason = queue.is_production_locked()
    assert locked is False
    assert reason is None

    # Lock production
    queue.lock_production("P0 incident detected: inc-123")

    # Should be locked
    locked, reason = queue.is_production_locked()
    assert locked is True
    assert reason == "P0 incident detected: inc-123"

    # Unlock production
    queue.unlock_production()

    # Should be unlocked again
    locked, reason = queue.is_production_locked()
    assert locked is False
    assert reason is None


@pytest.mark.asyncio
async def test_queue_timeout():
    """Test that dequeue times out when queue is empty."""
    queue = IncidentQueue(max_queue_size=100)

    # Dequeue from empty queue with timeout
    start = datetime.now(UTC)
    incident = await queue.dequeue(timeout=0.5)
    end = datetime.now(UTC)

    assert incident is None
    # Should have waited ~0.5 seconds
    elapsed = (end - start).total_seconds()
    assert 0.4 <= elapsed <= 0.7  # Allow some tolerance


@pytest.mark.asyncio
async def test_priority_from_severity_mapping():
    """Test that IncidentPriority.from_severity() maps correctly."""
    from aegis.agent.state import IncidentSeverity

    # CRITICAL → P0
    assert IncidentPriority.from_severity(IncidentSeverity.CRITICAL) == IncidentPriority.P0

    # HIGH → P1
    assert IncidentPriority.from_severity(IncidentSeverity.HIGH) == IncidentPriority.P1

    # MEDIUM → P2
    assert IncidentPriority.from_severity(IncidentSeverity.MEDIUM) == IncidentPriority.P2

    # LOW → P3
    assert IncidentPriority.from_severity(IncidentSeverity.LOW) == IncidentPriority.P3

    # INFO → P4
    assert IncidentPriority.from_severity(IncidentSeverity.INFO) == IncidentPriority.P4


@pytest.mark.asyncio
async def test_queue_metrics():
    """Test that queue metrics are tracked correctly."""
    queue = IncidentQueue(max_queue_size=100)

    # Create and enqueue some incidents
    state1 = create_initial_state("Pod", "pod-1", "default")
    state1["priority"] = IncidentPriority.P0
    state1["incident_id"] = "inc-1"

    state2 = create_initial_state("Pod", "pod-2", "default")
    state2["priority"] = IncidentPriority.P1
    state2["incident_id"] = "inc-2"

    await queue.enqueue(state1)
    await queue.enqueue(state2)

    # Check metrics
    metrics = queue.get_metrics()
    assert metrics["total_enqueued"] == 2
    assert metrics["total_dequeued"] == 0
    assert metrics["depth_by_priority"]["p0"] == 1
    assert metrics["depth_by_priority"]["p1"] == 1

    # Dequeue one
    await queue.dequeue(timeout=1.0)

    metrics = queue.get_metrics()
    assert metrics["total_dequeued"] == 1
    assert metrics["depth_by_priority"]["p0"] == 0
    assert metrics["depth_by_priority"]["p1"] == 1


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test that queue handles concurrent enqueue/dequeue operations."""
    queue = IncidentQueue(max_queue_size=100)

    async def producer():
        """Enqueue 10 incidents."""
        for i in range(10):
            state = create_initial_state("Pod", f"pod-{i}", "default")
            state["priority"] = IncidentPriority.P2
            state["incident_id"] = f"inc-{i}"
            await queue.enqueue(state)
            await asyncio.sleep(0.01)  # Small delay

    async def consumer():
        """Dequeue 10 incidents."""
        count = 0
        while count < 10:
            incident = await queue.dequeue(timeout=1.0)
            if incident:
                count += 1
                await asyncio.sleep(0.01)  # Small delay

    # Run producer and consumer concurrently
    await asyncio.gather(producer(), consumer())

    # Queue should be empty
    metrics = queue.get_metrics()
    assert metrics["total_enqueued"] == 10
    assert metrics["total_dequeued"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
