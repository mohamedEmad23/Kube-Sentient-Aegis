"""Incident Priority Queue System.

Manages incident processing with priority-based queuing, correlation,
and production deployment locking during critical incidents.

Features:
- P0-P4 priority queue (P0 = highest priority)
- Incident correlation and deduplication
- Production deployment locking during P0 incidents
- Thread-safe for concurrent operator handlers
- Metrics tracking (queue depth, processing time)
"""

import asyncio
import hashlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from aegis.agent.state import IncidentPriority, IncidentState
from aegis.observability._logging import get_logger


log = get_logger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass(order=True)
class QueuedIncident:
    """Incident wrapper for priority queue.

    Priority queue orders by:
    1. Priority value (P0=0 highest, P4=4 lowest)
    2. Creation timestamp (earlier = higher priority)
    """

    priority_value: int  # 0=P0, 1=P1, 2=P2, 3=P3, 4=P4
    created_at: datetime = field(compare=True)
    incident: IncidentState = field(compare=False)
    incident_id: str = field(compare=False)
    correlation_key: str = field(compare=False)


@dataclass
class IncidentMetrics:
    """Metrics for incident processing."""

    total_enqueued: int = 0
    total_dequeued: int = 0
    total_correlated: int = 0  # Deduplicated incidents
    queue_depth_by_priority: dict[str, int] = field(default_factory=dict)
    processing_time_seconds: list[float] = field(default_factory=list)


# ============================================================================
# Incident Queue
# ============================================================================


class IncidentQueue:
    """Priority-based incident queue with correlation and production locking.

    Example:
        >>> queue = IncidentQueue(correlation_window_seconds=300)
        >>> incident_id = await queue.enqueue(state)
        >>> incident = await queue.dequeue()  # Gets highest priority
        >>> queue.lock_production("P0 incident active")
        >>> queue.unlock_production()
    """

    def __init__(
        self,
        *,
        correlation_window_seconds: int = 300,
        max_queue_size: int = 100,
    ) -> None:
        """Initialize incident queue.

        Args:
            correlation_window_seconds: Time window for incident correlation (default: 5min)
            max_queue_size: Maximum incidents in queue before rejection
        """
        self._queue: asyncio.PriorityQueue[QueuedIncident] = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self._correlation_map: dict[str, QueuedIncident] = {}  # key -> incident
        self._correlation_window = timedelta(seconds=correlation_window_seconds)
        self._production_locked = False
        self._production_lock_reason: str | None = None
        self._lock = asyncio.Lock()
        self._metrics = IncidentMetrics()

    def _generate_incident_id(self) -> str:
        """Generate unique incident ID.

        Returns:
            ID format: inc-20260204-225430-abc123
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        unique = uuid.uuid4().hex[:6]
        return f"inc-{timestamp}-{unique}"

    def _correlation_key(self, state: IncidentState) -> str:
        """Generate correlation key for deduplication.

        Key format: namespace/resource_type/resource_name

        Args:
            state: Incident state

        Returns:
            Correlation key string
        """
        key_str = f"{state['namespace']}/{state['resource_type']}/{state['resource_name']}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def _priority_to_int(self, priority: IncidentPriority) -> int:
        """Convert IncidentPriority to integer for queue ordering.

        Args:
            priority: IncidentPriority enum value

        Returns:
            Integer: 0=P0 (highest), 4=P4 (lowest)
        """
        mapping = {
            IncidentPriority.P0: 0,
            IncidentPriority.P1: 1,
            IncidentPriority.P2: 2,
            IncidentPriority.P3: 3,
            IncidentPriority.P4: 4,
        }
        return mapping.get(priority, 3)  # Default to P3

    async def _cleanup_old_correlations(self) -> None:
        """Remove expired incidents from correlation map."""
        now = datetime.now(UTC)
        cutoff = now - self._correlation_window

        expired_keys = [
            key for key, queued in self._correlation_map.items() if queued.created_at < cutoff
        ]

        for key in expired_keys:
            del self._correlation_map[key]
            log.debug("correlation_expired", key=key)

    async def enqueue(
        self,
        incident: IncidentState,
        *,
        on_duplicate: Callable[[str], None] | None = None,
    ) -> str:
        """Enqueue incident with correlation check.

        Args:
            incident: IncidentState to enqueue
            on_duplicate: Optional callback when duplicate detected

        Returns:
            incident_id: Unique ID (existing if correlated, new otherwise)

        Raises:
            asyncio.QueueFull: If queue is at max capacity
        """
        async with self._lock:
            await self._cleanup_old_correlations()

            # Generate correlation key
            corr_key = self._correlation_key(incident)

            # Check for existing correlated incident
            if corr_key in self._correlation_map:
                existing = self._correlation_map[corr_key]
                self._metrics.total_correlated += 1

                log.info(
                    "incident_correlated",
                    incident_id=existing.incident_id,
                    resource=f"{incident['resource_type']}/{incident['resource_name']}",
                    namespace=incident["namespace"],
                )

                if on_duplicate:
                    on_duplicate(existing.incident_id)

                return existing.incident_id

            # New incident - assign ID and priority
            incident_id = self._generate_incident_id()
            incident["incident_id"] = incident_id

            # Assign priority if not set
            priority = incident.get("priority")
            if not priority and incident.get("rca_result"):
                # Map from RCA severity
                severity = incident["rca_result"].severity
                priority = IncidentPriority.from_severity(severity)
                incident["priority"] = priority
            elif not priority:
                priority = IncidentPriority.P3  # Default
                incident["priority"] = priority

            # Create queued incident
            queued = QueuedIncident(
                priority_value=self._priority_to_int(priority),
                created_at=datetime.now(UTC),
                incident=incident,
                incident_id=incident_id,
                correlation_key=corr_key,
            )

            # Add to queue and correlation map
            await self._queue.put(queued)
            self._correlation_map[corr_key] = queued

            # Update metrics
            self._metrics.total_enqueued += 1
            priority_str = priority.value
            self._metrics.queue_depth_by_priority[priority_str] = (
                self._metrics.queue_depth_by_priority.get(priority_str, 0) + 1
            )

            log.info(
                "incident_enqueued",
                incident_id=incident_id,
                priority=priority.value,
                resource=f"{incident['resource_type']}/{incident['resource_name']}",
                namespace=incident["namespace"],
                queue_depth=self._queue.qsize(),
            )

            # Auto-lock production if P0
            if priority == IncidentPriority.P0:
                self.lock_production(f"P0 incident active: {incident_id}")

            return incident_id

    async def dequeue(self, *, timeout: float | None = None) -> IncidentState | None:
        """Dequeue highest priority incident.

        Args:
            timeout: Optional timeout in seconds (None = block indefinitely)

        Returns:
            IncidentState or None if timeout/queue empty
        """
        try:
            if timeout is not None:
                queued = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                queued = await self._queue.get()
        except TimeoutError:
            return None

        async with self._lock:
            # Remove from correlation map
            if queued.correlation_key in self._correlation_map:
                del self._correlation_map[queued.correlation_key]

            # Update metrics
            self._metrics.total_dequeued += 1
            priority_str = queued.incident.get("priority", IncidentPriority.P3).value
            current_depth = self._metrics.queue_depth_by_priority.get(priority_str, 1)
            self._metrics.queue_depth_by_priority[priority_str] = max(0, current_depth - 1)

            log.info(
                "incident_dequeued",
                incident_id=queued.incident_id,
                priority=priority_str,
                queue_depth=self._queue.qsize(),
            )

            self._queue.task_done()

            return queued.incident

    def lock_production(self, reason: str) -> None:
        """Lock production deployments.

        Args:
            reason: Reason for lock (e.g., "P0 incident active")
        """
        self._production_locked = True
        self._production_lock_reason = reason
        log.warning("production_locked", reason=reason)

    def unlock_production(self) -> None:
        """Unlock production deployments."""
        self._production_locked = False
        self._production_lock_reason = None
        log.info("production_unlocked")

    def is_production_locked(self) -> tuple[bool, str | None]:
        """Check if production is locked.

        Returns:
            Tuple of (locked, reason)
        """
        return (self._production_locked, self._production_lock_reason)

    def get_metrics(self) -> dict[str, Any]:
        """Get current queue metrics.

        Returns:
            Dict with queue stats
        """
        return {
            "total_enqueued": self._metrics.total_enqueued,
            "total_dequeued": self._metrics.total_dequeued,
            "total_correlated": self._metrics.total_correlated,
            "current_depth": self._queue.qsize(),
            "depth_by_priority": self._metrics.queue_depth_by_priority.copy(),
            "production_locked": self._production_locked,
            "production_lock_reason": self._production_lock_reason,
        }

    def qsize(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


# ============================================================================
# Global Queue Instance
# ============================================================================

_global_queue: IncidentQueue | None = None


def get_incident_queue() -> IncidentQueue:
    """Get or create global incident queue.

    Returns:
        IncidentQueue singleton instance
    """
    global _global_queue
    if _global_queue is None:
        _global_queue = IncidentQueue()
    return _global_queue


__all__ = [
    "IncidentQueue",
    "QueuedIncident",
    "get_incident_queue",
]
