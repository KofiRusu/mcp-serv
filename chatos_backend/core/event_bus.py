"""
EventBus - Central Pub-Sub System for ChatOS Thought-Line Processing

This module provides a centralized event distribution system that enables:
- Real-time event propagation from scrapers to processing layers
- Thought engine coordination and status broadcasting
- Audit trail event logging
- UI status updates via WebSocket bridge

Event Types:
- market.tick, market.trade, market.liquidation, market.oi_update
- thought.created, thought.started, thought.completed, thought.blocked
- filter.passed, filter.warned, filter.blocked
- decision.made, decision.conflict
- execution.started, execution.completed, execution.error
- risk.warning, risk.blocked, risk.kill_switch
- audit.recorded, audit.replayed
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Represents a system event."""
    event_type: str
    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: EventPriority = EventPriority.NORMAL
    source: str = "system"
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:12]),
            event_type=data["event_type"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            priority=EventPriority(data.get("priority", 1)),
            source=data.get("source", "system"),
            correlation_id=data.get("correlation_id"),
        )


HandlerType = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Central pub-sub event bus for system-wide event coordination.
    
    Features:
    - Async event handling with priority queuing
    - Wildcard subscriptions (e.g., "market.*")
    - Event history for replay/debugging
    - Dead letter queue for failed events
    - Metrics tracking
    """
    
    def __init__(
        self,
        max_history: int = 1000,
        max_dead_letters: int = 100,
        handler_timeout: float = 5.0,
    ):
        self._handlers: Dict[str, List[HandlerType]] = defaultdict(list)
        self._wildcard_handlers: Dict[str, List[HandlerType]] = defaultdict(list)
        self._event_history: List[Event] = []
        self._dead_letters: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._max_dead_letters = max_dead_letters
        self._handler_timeout = handler_timeout
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        
        self._metrics = {
            "events_published": 0,
            "events_delivered": 0,
            "events_failed": 0,
            "handlers_called": 0,
            "handlers_failed": 0,
        }
    
    async def start(self):
        """Start the event bus processing loop."""
        if self._running:
            return
        
        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("EventBus started")
    
    async def stop(self):
        """Stop the event bus."""
        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")
    
    async def _process_events(self):
        """Main event processing loop."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._dispatch_event(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
    
    async def _dispatch_event(self, event: Event):
        """Dispatch event to all matching handlers."""
        handlers = self._get_handlers(event.event_type)
        
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type}")
            return
        
        for handler in handlers:
            try:
                await asyncio.wait_for(
                    handler(event),
                    timeout=self._handler_timeout
                )
                self._metrics["handlers_called"] += 1
            except asyncio.TimeoutError:
                logger.warning(f"Handler timeout for event {event.event_type}")
                self._metrics["handlers_failed"] += 1
            except Exception as e:
                logger.error(f"Handler error for event {event.event_type}: {e}")
                self._metrics["handlers_failed"] += 1
                self._add_dead_letter(event, handler, str(e))
        
        self._metrics["events_delivered"] += 1
    
    def _get_handlers(self, event_type: str) -> List[HandlerType]:
        """Get all handlers matching an event type, including wildcards."""
        handlers = list(self._handlers.get(event_type, []))
        
        parts = event_type.split(".")
        if len(parts) >= 1:
            wildcard = f"{parts[0]}.*"
            handlers.extend(self._wildcard_handlers.get(wildcard, []))
        
        handlers.extend(self._wildcard_handlers.get("*", []))
        
        return handlers
    
    def _add_dead_letter(self, event: Event, handler: HandlerType, error: str):
        """Add failed event to dead letter queue."""
        self._dead_letters.append({
            "event": event.to_dict(),
            "handler": handler.__name__,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        if len(self._dead_letters) > self._max_dead_letters:
            self._dead_letters = self._dead_letters[-self._max_dead_letters:]
    
    async def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "system",
        correlation_id: Optional[str] = None,
    ) -> Event:
        """
        Publish an event to the bus.
        
        Args:
            event_type: Type of event (e.g., "market.trade", "thought.completed")
            payload: Event data dictionary
            priority: Event priority for ordering
            source: Source identifier
            correlation_id: Optional ID to correlate related events
        
        Returns:
            The created Event object
        """
        event = Event(
            event_type=event_type,
            payload=payload,
            priority=priority,
            source=source,
            correlation_id=correlation_id,
        )
        
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        await self._event_queue.put(event)
        self._metrics["events_published"] += 1
        
        logger.debug(f"Published event: {event_type} (id={event.id})")
        return event
    
    def publish_sync(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "system",
    ) -> Event:
        """
        Synchronously queue an event (for use in non-async contexts).
        """
        event = Event(
            event_type=event_type,
            payload=payload,
            priority=priority,
            source=source,
        )
        
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        try:
            self._event_queue.put_nowait(event)
            self._metrics["events_published"] += 1
        except asyncio.QueueFull:
            logger.warning(f"Event queue full, dropping event: {event_type}")
            self._metrics["events_failed"] += 1
        
        return event
    
    def subscribe(self, event_type: str, handler: HandlerType):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type to subscribe to. Use "*" for all events,
                       or "prefix.*" for wildcard matching.
            handler: Async function to call when event is received
        """
        if event_type.endswith(".*") or event_type == "*":
            self._wildcard_handlers[event_type].append(handler)
        else:
            self._handlers[event_type].append(handler)
        
        logger.debug(f"Subscribed handler {handler.__name__} to {event_type}")
    
    def unsubscribe(self, event_type: str, handler: HandlerType):
        """Unsubscribe a handler from an event type."""
        if event_type.endswith(".*") or event_type == "*":
            handlers = self._wildcard_handlers.get(event_type, [])
        else:
            handlers = self._handlers.get(event_type, [])
        
        if handler in handlers:
            handlers.remove(handler)
            logger.debug(f"Unsubscribed handler {handler.__name__} from {event_type}")
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[Event]:
        """Get event history, optionally filtered."""
        events = self._event_history
        
        if event_type:
            if event_type.endswith(".*"):
                prefix = event_type[:-2]
                events = [e for e in events if e.event_type.startswith(prefix)]
            else:
                events = [e for e in events if e.event_type == event_type]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events[-limit:]
    
    def get_dead_letters(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get dead letter queue entries."""
        return self._dead_letters[-limit:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics."""
        return {
            **self._metrics,
            "queue_size": self._event_queue.qsize(),
            "handler_count": sum(len(h) for h in self._handlers.values()) + sum(len(h) for h in self._wildcard_handlers.values()),
            "history_size": len(self._event_history),
            "dead_letter_count": len(self._dead_letters),
        }
    
    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()
    
    def clear_dead_letters(self):
        """Clear dead letter queue."""
        self._dead_letters.clear()


_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def init_event_bus() -> EventBus:
    """Initialize and start the event bus."""
    bus = get_event_bus()
    await bus.start()
    return bus


async def shutdown_event_bus():
    """Shutdown the event bus."""
    global _event_bus
    if _event_bus:
        await _event_bus.stop()
        _event_bus = None
