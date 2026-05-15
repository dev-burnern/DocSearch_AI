from datetime import UTC, datetime, timedelta

from backend.app.audit.models import AuditCitation, ChatAuditEvent
from backend.app.audit.models import ChatAuditEventFilters
from backend.app.audit.store import InMemoryAuditLogStore


def _event(
    workspace_id: str,
    question: str,
    *,
    request_id: str = "request-1",
    document_ids: list[str] | None = None,
    occurred_at: datetime | None = None,
    answer_preview: str = "요약 답변입니다.",
) -> ChatAuditEvent:
    return ChatAuditEvent(
        request_id=request_id,
        occurred_at=occurred_at or datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
        workspace_id=workspace_id,
        workspace_name=f"{workspace_id} name",
        question=question,
        document_ids=document_ids or ["doc-1"],
        retrieval_limit=5,
        rerank_top_k=3,
        retrieved_chunk_count=1,
        model="google/gemma-4-E4B-it",
        answer_preview=answer_preview,
        answer_character_count=8,
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


def test_인메모리_감사로그_저장소가_워크스페이스별로_이벤트를_조회한다() -> None:
    store = InMemoryAuditLogStore()
    alpha_event = _event("workspace-alpha", "알파 질문")
    beta_event = _event("workspace-beta", "베타 질문")

    store.record_chat_event(alpha_event)
    store.record_chat_event(beta_event)

    events = store.list_chat_events(workspace_id="workspace-alpha")

    assert events == [alpha_event]


def test_인메모리_감사로그_저장소가_필터와_limit을_적용한다() -> None:
    store = InMemoryAuditLogStore()
    base_time = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)
    target = _event(
        "workspace-alpha",
        "보안 정책 요약해줘",
        request_id="request-target",
        document_ids=["doc-policy"],
        occurred_at=base_time,
        answer_preview="보안 정책 답변",
    )
    store.record_chat_event(
        _event(
            "workspace-alpha",
            "보안 정책 이전 기록",
            request_id="request-old",
            document_ids=["doc-policy"],
            occurred_at=base_time - timedelta(days=1),
        )
    )
    store.record_chat_event(target)
    store.record_chat_event(
        _event(
            "workspace-alpha",
            "다른 문서 질문",
            request_id="request-other",
            document_ids=["doc-other"],
            occurred_at=base_time,
        )
    )

    events = store.list_chat_events(
        workspace_id="workspace-alpha",
        filters=ChatAuditEventFilters(
            query="보안",
            document_id="doc-policy",
            request_id="request-target",
            occurred_from=base_time - timedelta(hours=1),
            occurred_to=base_time + timedelta(hours=1),
            limit=1,
        ),
    )

    assert events == [target]


def test_감사로그_필터는_타임존이_없는_시각을_UTC로_해석한다() -> None:
    store = InMemoryAuditLogStore()
    target = _event(
        "workspace-alpha",
        "시간 필터 질문",
        occurred_at=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
    )
    store.record_chat_event(target)

    events = store.list_chat_events(
        workspace_id="workspace-alpha",
        filters=ChatAuditEventFilters(
            occurred_from=datetime(2026, 5, 15, 8, 0),
            occurred_to=datetime(2026, 5, 15, 10, 0),
        ),
    )

    assert events == [target]
