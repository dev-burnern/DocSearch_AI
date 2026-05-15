from datetime import UTC, datetime

from fastapi.testclient import TestClient
import pytest

from backend.app.audit.models import AuditCitation, ChatAuditEvent, ChatAuditEventFilters
from backend.app.audit.store import InMemoryAuditLogStore
from backend.app.core.config import get_settings
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_감사로그_API가_워크스페이스_이벤트만_반환한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )
    store = InMemoryAuditLogStore()
    store.record_chat_event(
        ChatAuditEvent(
            request_id="request-alpha",
            workspace_id="workspace-alpha",
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
    )
    store.record_chat_event(
        ChatAuditEvent(
            request_id="request-beta",
            workspace_id="workspace-beta",
            workspace_name="Workspace Beta",
            question="다른 워크스페이스 질문",
            document_ids=None,
            retrieval_limit=5,
            rerank_top_k=3,
            retrieved_chunk_count=0,
            model="google/gemma-4-E4B-it",
            answer_preview="다른 답변",
            answer_character_count=5,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            citations=[],
        )
    )

    from backend.app.audit.router import get_audit_log_store

    app = create_app()
    app.dependency_overrides[get_audit_log_store] = lambda: store
    client = TestClient(app)

    response = client.get(
        "/v1/audit-logs/chat",
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["events"][0]["request_id"] == "request-alpha"
    assert body["events"][0]["workspace_id"] == "workspace-alpha"
    assert body["events"][0]["question"] == "정책 문서 요약해줘"
    assert body["events"][0]["citations"][0]["rerank_score"] == 0.9


class CapturingAuditLogStore:
    def __init__(self) -> None:
        self.filters: ChatAuditEventFilters | None = None

    def record_chat_event(self, event: ChatAuditEvent) -> None:
        return None

    def list_chat_events(
        self,
        *,
        workspace_id: str,
        filters: ChatAuditEventFilters | None = None,
    ) -> list[ChatAuditEvent]:
        self.filters = filters
        return []


def test_감사로그_API가_쿼리_필터를_저장소로_전달한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )
    store = CapturingAuditLogStore()

    from backend.app.audit.router import get_audit_log_store

    app = create_app()
    app.dependency_overrides[get_audit_log_store] = lambda: store
    client = TestClient(app)

    response = client.get(
        "/v1/audit-logs/chat",
        params={
            "query": "정책",
            "document_id": "doc-1",
            "request_id": "request-1",
            "from": "2026-05-15T09:00:00Z",
            "to": "2026-05-15T10:00:00Z",
            "limit": "20",
        },
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 200
    assert store.filters == ChatAuditEventFilters(
        query="정책",
        document_id="doc-1",
        request_id="request-1",
        occurred_from=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
        occurred_to=datetime(2026, 5, 15, 10, 0, tzinfo=UTC),
        limit=20,
    )
