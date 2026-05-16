from datetime import UTC, datetime
from threading import Lock
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


OperationEventSeverity = Literal["info", "warning", "error"]


class OperationEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    severity: OperationEventSeverity
    source: str
    message: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, str] = Field(default_factory=dict)


class OperationEventStore(Protocol):
    def record(self, event: OperationEvent) -> None:
        raise NotImplementedError

    def list_events(self, *, limit: int = 20) -> list[OperationEvent]:
        raise NotImplementedError


class InMemoryOperationEventStore:
    def __init__(self, *, max_events: int = 200) -> None:
        self._max_events = max_events
        self._events: list[OperationEvent] = []
        self._lock = Lock()

    def record(self, event: OperationEvent) -> None:
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events :]

    def list_events(self, *, limit: int = 20) -> list[OperationEvent]:
        with self._lock:
            return list(reversed(self._events[-limit:]))
