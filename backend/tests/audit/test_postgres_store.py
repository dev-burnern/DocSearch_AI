import json

from backend.app.audit.models import AuditCitation, ChatAuditEvent
from backend.app.audit.postgres_store import PostgresAuditLogStore


class FakeCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[tuple[str, dict[str, object] | None]] = []
        self.commit_count = 0

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def execute(
        self,
        sql: str,
        params: dict[str, object] | None = None,
    ) -> FakeCursor:
        self.statements.append((sql, params))
        return FakeCursor(self.rows)

    def commit(self) -> None:
        self.commit_count += 1


def _event(workspace_id: str = "workspace-alpha") -> ChatAuditEvent:
    return ChatAuditEvent(
        request_id="request-1",
        workspace_id=workspace_id,
        workspace_name="Workspace Alpha",
        question="정책 문서 요약해줘",
        document_ids=["doc-1"],
        retrieval_limit=5,
        rerank_top_k=3,
        retrieved_chunk_count=1,
        model="google/gemma-4-E4B-it",
        answer_preview="답변입니다.",
        answer_character_count=5,
        prompt_tokens=10,
        completion_tokens=4,
        total_tokens=14,
        citations=[
            AuditCitation(
                citation_id=1,
                document_id="doc-1",
                filename="policy.md",
                chunk_index=0,
                score=0.8,
                rerank_score=0.9,
            )
        ],
    )


def test_PostgresAuditLogStore가_스키마를_보장하고_이벤트를_jsonb로_저장한다() -> None:
    connection = FakeConnection()
    store = PostgresAuditLogStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        connection_factory=lambda: connection,
    )

    store.record_chat_event(_event())

    assert "CREATE TABLE IF NOT EXISTS chat_audit_events" in connection.statements[0][0]
    insert_sql, insert_params = connection.statements[2]
    assert "INSERT INTO chat_audit_events" in insert_sql
    assert insert_params is not None
    assert insert_params["workspace_id"] == "workspace-alpha"
    assert insert_params["request_id"] == "request-1"
    payload = json.loads(str(insert_params["event_payload"]))
    assert payload["question"] == "정책 문서 요약해줘"
    assert payload["citations"][0]["rerank_score"] == 0.9
    assert connection.commit_count == 2


def test_PostgresAuditLogStore가_jsonb_payload를_이벤트로_복원한다() -> None:
    event = _event()
    connection = FakeConnection(
        rows=[{"event_payload": event.model_dump(mode="json")}],
    )
    store = PostgresAuditLogStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        connection_factory=lambda: connection,
    )

    events = store.list_chat_events(workspace_id="workspace-alpha")

    assert events == [event]
    select_sql, select_params = connection.statements[-1]
    assert "WHERE workspace_id = %(workspace_id)s" in select_sql
    assert select_params == {"workspace_id": "workspace-alpha", "limit": 100}
