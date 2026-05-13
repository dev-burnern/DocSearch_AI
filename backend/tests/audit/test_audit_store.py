from backend.app.audit.models import AuditCitation, ChatAuditEvent
from backend.app.audit.store import InMemoryAuditLogStore


def _event(workspace_id: str, question: str) -> ChatAuditEvent:
    return ChatAuditEvent(
        request_id="request-1",
        workspace_id=workspace_id,
        workspace_name=f"{workspace_id} name",
        question=question,
        document_ids=["doc-1"],
        retrieval_limit=5,
        rerank_top_k=3,
        retrieved_chunk_count=1,
        model="google/gemma-4-E4B-it",
        answer_preview="요약 답변입니다.",
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
