from threading import Lock
from typing import Protocol

from backend.app.audit.models import ChatAuditEvent, ChatAuditEventFilters


class AuditLogStore(Protocol):
    def record_chat_event(self, event: ChatAuditEvent) -> None:
        raise NotImplementedError

    def list_chat_events(
        self,
        *,
        workspace_id: str,
        filters: ChatAuditEventFilters | None = None,
    ) -> list[ChatAuditEvent]:
        raise NotImplementedError


class InMemoryAuditLogStore:
    def __init__(self) -> None:
        self._events: list[ChatAuditEvent] = []
        self._lock = Lock()

    def record_chat_event(self, event: ChatAuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def list_chat_events(
        self,
        *,
        workspace_id: str,
        filters: ChatAuditEventFilters | None = None,
    ) -> list[ChatAuditEvent]:
        resolved_filters = filters or ChatAuditEventFilters()
        with self._lock:
            events = [
                event
                for event in self._events
                if event.workspace_id == workspace_id
                and _matches_filters(event, resolved_filters)
            ]

        return sorted(
            events,
            key=lambda event: event.occurred_at,
            reverse=True,
        )[: resolved_filters.limit]


def _matches_filters(
    event: ChatAuditEvent,
    filters: ChatAuditEventFilters,
) -> bool:
    if filters.event_type and event.event_type != filters.event_type:
        return False

    if filters.request_id and event.request_id != filters.request_id:
        return False

    if filters.document_id and not _has_document_id(event, filters.document_id):
        return False

    if filters.occurred_from and event.occurred_at < filters.occurred_from:
        return False

    if filters.occurred_to and event.occurred_at > filters.occurred_to:
        return False

    if filters.query:
        query = filters.query.lower()
        searchable_text = f"{event.question}\n{event.answer_preview}".lower()
        if query not in searchable_text:
            return False

    return True


def _has_document_id(event: ChatAuditEvent, document_id: str) -> bool:
    if event.document_ids and document_id in event.document_ids:
        return True

    return any(citation.document_id == document_id for citation in event.citations)
