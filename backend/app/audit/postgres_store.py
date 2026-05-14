import json
from typing import Callable

from backend.app.audit.models import ChatAuditEvent


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
        limit: int = 100,
    ) -> list[ChatAuditEvent]:
        with self._connection_factory() as connection:
            cursor = connection.execute(
                """
                SELECT event_payload
                FROM chat_audit_events
                WHERE workspace_id = %(workspace_id)s
                ORDER BY occurred_at DESC
                LIMIT %(limit)s
                """,
                {"workspace_id": workspace_id, "limit": limit},
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
