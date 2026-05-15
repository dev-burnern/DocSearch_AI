import csv
from datetime import UTC, datetime
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from backend.app.audit.export import build_chat_audit_csv
from backend.app.audit.models import AuditCitation, ChatAuditEvent
from backend.app.audit.store import InMemoryAuditLogStore
from backend.app.core.config import get_settings
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _event(
    *,
    workspace_id: str = "workspace-alpha",
    workspace_name: str = "Workspace Alpha",
    question: str = "정책 문서 요약해줘",
    answer_preview: str = "답변입니다.",
    request_id: str = "request-1",
) -> ChatAuditEvent:
    return ChatAuditEvent(
        event_id=f"event-{request_id}",
        occurred_at=datetime(2026, 5, 15, 9, 30, tzinfo=UTC),
        request_id=request_id,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        question=question,
        document_ids=["doc-1", "doc-2"],
        retrieval_limit=5,
        rerank_top_k=3,
        retrieved_chunk_count=2,
        model="google/gemma-4-E4B-it",
        answer_preview=answer_preview,
        answer_character_count=len(answer_preview),
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
            ),
            AuditCitation(
                citation_id=2,
                document_id="doc-2",
                filename="guide.csv",
                chunk_index=1,
                score=0.7,
                rerank_score=None,
            ),
        ],
    )


def test_채팅_감사로그를_CSV로_직렬화한다() -> None:
    csv_text = build_chat_audit_csv([_event()])

    rows = list(csv.DictReader(StringIO(csv_text)))

    assert rows == [
        {
            "이벤트 ID": "event-request-1",
            "발생 시각": "2026-05-15T09:30:00Z",
            "이벤트 유형": "chat.answer.generated",
            "워크스페이스 ID": "workspace-alpha",
            "워크스페이스 이름": "Workspace Alpha",
            "요청 ID": "request-1",
            "질문": "정책 문서 요약해줘",
            "답변 미리보기": "답변입니다.",
            "문서 ID": "doc-1; doc-2",
            "출처 파일": "policy.md; guide.csv",
            "검색 제한": "5",
            "리랭크 상위 K": "3",
            "검색 청크 수": "2",
            "모델": "google/gemma-4-E4B-it",
            "프롬프트 토큰": "10",
            "완료 토큰": "4",
            "전체 토큰": "14",
        }
    ]


def test_CSV_직렬화가_쉼표와_줄바꿈과_따옴표를_보존한다() -> None:
    event = _event(
        question='정책, "보안" 문서를\n요약해줘',
        answer_preview='첫 줄 답변,\n"둘째 줄" 답변',
    )

    rows = list(csv.DictReader(StringIO(build_chat_audit_csv([event]))))

    assert rows[0]["질문"] == '정책, "보안" 문서를\n요약해줘'
    assert rows[0]["답변 미리보기"] == '첫 줄 답변,\n"둘째 줄" 답변'


def test_감사로그_내보내기_API가_워크스페이스와_필터를_적용한_CSV를_반환한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )
    store = InMemoryAuditLogStore()
    store.record_chat_event(_event(question="정책 문서 요약해줘"))
    store.record_chat_event(_event(question="다른 질문", request_id="request-other"))
    store.record_chat_event(
        _event(
            workspace_id="workspace-beta",
            workspace_name="Workspace Beta",
            question="정책 문서 요약해줘",
            request_id="request-beta",
        )
    )

    from backend.app.audit.router import get_audit_log_store

    app = create_app()
    app.dependency_overrides[get_audit_log_store] = lambda: store
    client = TestClient(app)

    response = client.get(
        "/v1/audit-logs/chat/export",
        params={"query": "정책", "limit": "20"},
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "chat-audit-logs-" in response.headers["content-disposition"]

    rows = list(csv.DictReader(StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["요청 ID"] == "request-1"
    assert rows[0]["워크스페이스 ID"] == "workspace-alpha"
