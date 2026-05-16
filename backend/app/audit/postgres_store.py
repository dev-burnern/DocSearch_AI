import json
from typing import Callable

from backend.app.audit.models import ChatAuditEvent, ChatAuditEventFilters


class PostgresAuditLogStore:
    def __init__(
        self,
        *,
        database_url: str,
        connection_factory: Callable[[], object] | None = None,
    ) -> None:
        self._database_url = database_url
        self._connection_factory = connection_factory or self._create_connection
        self._ensure_schema()

    def record_chat_event(self, event: ChatAuditEvent) -> None:
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        params = {
            "event_id": event.event_id,
            "request_id": event.request_id,
            "workspace_id": event.workspace_id,
            "workspace_name": event.workspace_name,
            "event_type": event.event_type,
            "occurred_at": event.occurred_at,
            "event_payload": payload,
        }
        with self._connection_factory() as connection:
            connection.execute(
                """
                INSERT INTO chat_audit_events (
                    event_id,
                    request_id,
                    workspace_id,
                    workspace_name,
                    event_type,
                    occurred_at,
                    event_payload
                )
                VALUES (
                    %(event_id)s,
                    %(request_id)s,
                    %(workspace_id)s,
                    %(workspace_name)s,
                    %(event_type)s,
                    %(occurred_at)s,
                    %(event_payload)s::jsonb
                )
                """,
                params,
            )
            connection.commit()

    def list_chat_events(
        self,
        *,
        workspace_id: str,
        filters: ChatAuditEventFilters | None = None,
    ) -> list[ChatAuditEvent]:
        resolved_filters = filters or ChatAuditEventFilters()
        where_clauses, params = _build_filter_clauses(
            workspace_id=workspace_id,
            filters=resolved_filters,
        )
        with self._connection_factory() as connection:
            cursor = connection.execute(
                f"""
                SELECT event_payload
                FROM chat_audit_events
                WHERE {" AND ".join(where_clauses)}
                ORDER BY occurred_at DESC
                LIMIT %(limit)s
                """,
                params,
            )
            rows = cursor.fetchall()

        return [
            ChatAuditEvent.model_validate(_read_payload(row))
            for row in rows
        ]

    def _ensure_schema(self) -> None:
        with self._connection_factory() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_audit_events (
                    event_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    workspace_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TIMESTAMPTZ NOT NULL,
                    event_payload JSONB NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_audit_events_workspace_time
                ON chat_audit_events (workspace_id, occurred_at DESC)
                """
            )
            connection.commit()

    def _create_connection(self) -> object:
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._database_url, row_factory=dict_row)


def _read_payload(row: dict[str, object]) -> dict[str, object] | str:
    payload = row["event_payload"]
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def _build_filter_clauses(
    *,
    workspace_id: str,
    filters: ChatAuditEventFilters,
) -> tuple[list[str], dict[str, object]]:
    clauses = ["workspace_id = %(workspace_id)s"]
    params: dict[str, object] = {
        "workspace_id": workspace_id,
        "limit": filters.limit,
    }

    if filters.event_type:
        clauses.append("event_type = %(event_type)s")
        params["event_type"] = filters.event_type

    if filters.request_id:
        clauses.append("request_id = %(request_id)s")
        params["request_id"] = filters.request_id

    if filters.document_id:
        clauses.append(
            """
            (
                event_payload->'document_ids' ? %(document_id)s
                OR event_payload->'citations' @> jsonb_build_array(
                    jsonb_build_object('document_id', %(document_id)s)
                )
            )
            """
        )
        params["document_id"] = filters.document_id

    if filters.occurred_from:
        clauses.append("occurred_at >= %(occurred_from)s")
        params["occurred_from"] = filters.occurred_from

    if filters.occurred_to:
        clauses.append("occurred_at <= %(occurred_to)s")
        params["occurred_to"] = filters.occurred_to

    if filters.query:
        clauses.append(
            """
            (
                event_payload->>'question' ILIKE %(query_like)s
                OR event_payload->>'answer_preview' ILIKE %(query_like)s
            )
            """
        )
        params["query_like"] = f"%{filters.query}%"

    return clauses, params
