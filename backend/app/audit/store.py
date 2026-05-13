from threading import Lock
from typing import Protocol

from backend.app.audit.models import ChatAuditEvent


class AuditLogStore(Protocol):
    def record_chat_event(self, event: ChatAuditEvent) -> None:
        raise NotImplementedError

    def list_chat_events(self, *, workspace_id: str) -> list[ChatAuditEvent]:
        raise NotImplementedError


class InMemoryAuditLogStore:
    def __init__(self) -> None:
        self._events: list[ChatAuditEvent] = []
        self._lock = Lock()

    def record_chat_event(self, event: ChatAuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def list_chat_events(self, *, workspace_id: str) -> list[ChatAuditEvent]:
        with self._lock:
            return [
                event
                for event in self._events
                if event.workspace_id == workspace_id
            ]
